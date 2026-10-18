import numpy as np
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread

from fastapi import FastAPI, UploadFile, BackgroundTasks, Request, Form, Depends, APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from dotenv import load_dotenv
load_dotenv()

from config import Config
from r_types import Operation, OperationMode, default_ordered_options

import sys, os, logging, signal, asyncio, shutil, random, time, uuid
import convert

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

HOST = os.getenv("HOST", "0.0.0.0")
URL = os.getenv("URL", "http://127.0.0.1")
PORT = int(os.getenv("PORT", "80"))

lib_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
if os.path.exists(lib_dir):
    sys.path.append(lib_dir)

# device specific imports
try:
    from waveshare_epd import epd7in3e
    import buttons

    epd: epd7in3e.EPD
except Exception as e: #noqa: BLE001
    logger.warning(f"could not import waveshare or buttons, not running on pi zero:\n{e}")

wrk_dir = Path(os.path.dirname(os.path.realpath(__file__)))
pic_dir = Path(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'pictures'))
sttc_dir = Path(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static'))
config_dir = Path(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.json'))

class HardwareBusy(Exception):
    pass

def exit_callback(signum, frame):
    print(f"\nReceived exit signal ({signum}). Cleaning up...")
    try:
        if epd is not None:
            epd.sleep()
    except Exception as e: #noqa: BLE001
        print(f"Warning: Display Cleanup Failed: {e}")
    sys.exit()

signal.signal(signal.SIGINT, exit_callback)
signal.signal(signal.SIGTERM, exit_callback)

config: Config

hardware_lock = asyncio.Lock()

async def update(path: Path | None):
    if epd is None:
        logger.warning("Hardware not initialized. Skipping screen flash.")
        return

    async with hardware_lock:
        await asyncio.to_thread(_update_display, path)


def _update_display(path: Path | None):
    epd.init()
    if path is None:
        font = ImageFont.truetype(os.path.join(str(wrk_dir), 'Font.ttc'), 36)
        image = Image.new('RGB', (epd.width, epd.height), epd.WHITE)  # 255: clear the frame
        draw = ImageDraw.Draw(image)
        draw.text((10, 20), 'no image selected', font = font, fill = epd.RED)
        epd.display(epd.getbuffer(image))

    else:
        with Image.open(path) as frame_image:
            epd.display(epd.getbuffer(frame_image))

    logger.info("Hardware update finished. Putting display to deep sleep.")
    epd.sleep()


async def init():
    global config, epd
    try:
        config = await Config.create(config_dir)

        logger.info("Importing and initializing e-ink library")
        epd = epd7in3e.EPD()
        epd.init()
        epd.sleep()
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        epd = None

asyncio.run(init())

async def check_hardware():
    if epd is None:
        raise HardwareBusy()
    if hardware_lock.locked():
        raise HardwareBusy()

app = FastAPI()
update_router = APIRouter(dependencies=[Depends(check_hardware)])
app.mount("/pictures", StaticFiles(directory=pic_dir), name="pictures")
app.mount("/static", StaticFiles(directory=sttc_dir), name="static")

templates = Jinja2Templates(directory="templates")

async def process_and_refresh(file_path: Path):
    try:
        bmp_path = file_path.with_suffix(".bmp")
        with Image.open(file_path) as img:
            converted_img = convert.convert_to_bmp(img, default_ordered_options)
            converted_img.save(bmp_path, "BMP")

        if file_path != bmp_path:
            file_path.unlink()

        logger.info(f"Writing {bmp_path.name} to display...")
        config.data.current_picture = str(bmp_path.resolve())
        await config.save()
        await update(bmp_path)


    except Exception as e: #noqa: BLE001
        logger.error(f"Error during background refresh loop: {e}")


def get_next_image() -> Path | None:
    images = sorted([str(f.resolve()) for f in pic_dir.glob("*.bmp")])
    if len(images) == 0:
        logger.warning("no images")
        return None

    current = Path(config.data.current_picture)
    if config.data.current_picture == "":
        logger.warning("current not set")
        return None
    try:
        idx = images.index(str(current.resolve()))
        if config.data.operation.mode == 0 or config.data.operation.mode == 1:
            # sequential
            next_idx = (idx + 1) % len(images)
            next_img = images[next_idx]

        elif config.data.operation.mode == 2:
            # random
            next_img = random.choice(images)
        else:
            # default to sequential
            next_idx = (idx + 1) % len(images)
            next_img = images[next_idx]

    except ValueError as e:
        logger.warning(str(e))
        return None

    return Path(next_img)

def get_previous_image() -> Path | None:
    images = sorted([str(f.resolve()) for f in pic_dir.glob("*.bmp")])
    if len(images) == 0:
        logger.warning("no images")
        return None

    current = Path(config.data.current_picture)
    if config.data.current_picture == "":
        logger.warning("current not set")
        return None

    try:
        idx = images.index(str(current.resolve()))
        if config.data.operation.mode == 0 or config.data.operation.mode == 1:
            # sequential
            next_idx = idx - 1
            next_img = images[next_idx]

        elif config.data.operation.mode == 2:
            # random
            next_img = random.choice(images)
        else:
            # default to sequential
            next_idx = idx - 1
            next_img = images[next_idx]
    except ValueError as e:
        logger.warning(str(e))
        return None

    return Path(next_img)

def construct_alert_parameters(type: str = "message", title: str = "", text: str = "", timeout: int = 6):
    encoded = f"alert_type={type}&alert_title={title}&alert_text={text}&alert_timeout={timeout}"
    return encoded

def wants_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "").lower()

@app.middleware("http")
async def return_type(request: Request, call_next):
    request.state.wants_html = wants_html(request)

    response = await call_next(request)
    return response

@update_router.post("/select")
async def select_image(request: Request, background_tasks: BackgroundTasks, filename: str = Form(...)):
    file_path = (pic_dir / filename).resolve()
    picture_dir = pic_dir.resolve()

    use_html = request.state.wants_html

    if not file_path.is_file():
        if use_html:
            encoded_string = construct_alert_parameters(
                type="error",
                title="Not a file",
                text="Selected is not a file",
                timeout=6
            )
            return RedirectResponse(url=f"/?{encoded_string}", status_code=303)
        return {"status": "error", "error": "not a file"}

    if file_path.parent != picture_dir:
        if use_html:
            encoded_string = construct_alert_parameters(
                type="error",
                title="Path Mismatch",
                text="Path does not match systems",
                timeout=6
            )
            return RedirectResponse(url=f"/?{encoded_string}", status_code=303)
        return {"status": "error", "error": "path does not match systems"}

    config.data.current_picture = str(file_path.resolve())
    await config.save()
    background_tasks.add_task(update, file_path)

    if use_html:
        encoded_string = construct_alert_parameters(
            type="success",
            title="Updating",
            text="Can take up to 30 seconds",
            timeout=6
        )
        return RedirectResponse(url=f"/?{encoded_string}", status_code=303)
    return {"status": "ok", "error": "none"}


@update_router.post("/remove")
async def remove_image(request: Request, background_tasks: BackgroundTasks, filename: str = Form(...)):
    file_path = (pic_dir / filename).resolve()
    picture_dir = pic_dir.resolve()

    use_html = request.state.wants_html

    if file_path.parent != picture_dir:
        if use_html:
            encoded_string = construct_alert_parameters(
                type="error",
                title="Path Mismatch",
                text="Path does not match the systems",
                timeout=6
            )
            return RedirectResponse(url=f"/?{encoded_string}", status_code=303)
        return {"status": "error", "error": "path does not match systems"}


    current = Path(config.data.current_picture)
    if config.data.current_picture != "" and file_path == current.resolve():
        config.data.current_picture = ""
        await config.save()
        background_tasks.add_task(update, None)

    file_path.unlink(missing_ok=True)

    if use_html:
        encoded_string = construct_alert_parameters(
            type="success",
            title="Deleted",
            text="Image has been deleted",
            timeout=6
        )
        return RedirectResponse(url=f"/?{encoded_string}", status_code=303)
    return {"status": "ok", "error": "none"}

@update_router.post("/upload")
async def upload_image(request: Request, background_tasks: BackgroundTasks, file: UploadFile):
    filename = Path(file.filename).name if file.filename else str(uuid.uuid4())
    temp_file_path = pic_dir / filename
    with open(temp_file_path, "wb") as buffer: #noqa: ASYNC230
        shutil.copyfileobj(file.file, buffer)

    use_html = request.state.wants_html

    background_tasks.add_task(process_and_refresh, temp_file_path)

    if use_html:
        encoded_string = construct_alert_parameters(
            type="success",
            title="Updating",
            text="Can take up to 30 seconds",
            timeout=6
        )
        return RedirectResponse(url=f"/?{encoded_string}", status_code=303)
    return {"status": "ok", "error": "none"}

def operation_form(
        mode: OperationMode = Form(Operation.model_fields["mode"].default),
        start: str = Form(Operation.model_fields["start"].default),
        interval: int = Form(Operation.model_fields["interval"].default),
    ):
    return Operation(
        mode=mode,
        start=start,
        interval=interval,
    )

@app.post("/operation")
async def operation(request: Request, operation_data: Operation = Depends(operation_form)):
    use_html = request.state.wants_html

    now = datetime.now().astimezone()
    start_time = datetime.strptime(operation_data.start, "%H:%M").time()
    next_update = datetime.combine(now.date(), start_time, tzinfo=now.tzinfo)

    interval = config.data.operation.interval
    if next_update <= now:
        next_update += timedelta(hours=interval)

    config.data.next_update = int(next_update.timestamp())
    config.data.operation = operation_data
    await config.save()

    if use_html:
        encoded_string = construct_alert_parameters(
            type="success",
            title="Updated",
            text="Operation has been updated",
            timeout=6
        )
        return RedirectResponse(url=f"/?{encoded_string}", status_code=303)
    return {"status": "ok", "error": "none"}

@update_router.post("/trigger")
async def trigger(request: Request, background_tasks: BackgroundTasks):
    use_html = request.state.wants_html

    if config.data.operation.mode != OperationMode.STATIC:
        now = int(time.time())
        next_update = int(config.data.next_update)
        if now >= next_update:
            # change image based on operation mode, get_next_image() handles this
            next_image = get_next_image()
            if next_image is None:
                if use_html:
                    encoded_string = construct_alert_parameters(
                        type="error",
                        title="No Next Image",
                        text="Unable to get the next image",
                        timeout=6
                    )
                    return RedirectResponse(url=f"/?{encoded_string}", status_code=303)
                return {"status": "ok", "error": "no next image"}

            config.data.current_picture = str(next_image.resolve())
            background_tasks.add_task(update, next_image)

            interval_seconds = config.data.operation.interval * 60 * 60
            while next_update <= now:
                # keep adding hours until next is greater than,
                # prevents a constant loop if no power for a while
                next_update += interval_seconds

            config.data.next_update = int(next_update)
            await config.save()
        else:
            logger.debug(f"not time to trigger yet {next_update} > {now}")
    if use_html:
        encoded_string = construct_alert_parameters(
            type="success",
            title="Updating",
            text="Can take up to 30 seconds",
            timeout=6
        )
        return RedirectResponse(url=f"/?{encoded_string}", status_code=303)
    return {"status": "ok", "error": "none"}

@update_router.post("/refresh")
async def refresh(request: Request, background_tasks: BackgroundTasks):
    use_html = request.state.wants_html

    current = Path(config.data.current_picture)
    if config.data.current_picture == "":
        if use_html:
            encoded_string = construct_alert_parameters(
                type="error",
                title="Not set",
                text="Current image is not set",
                timeout=6
            )
            return RedirectResponse(url=f"/?{encoded_string}", status_code=303)
        return {"status": "error", "error": "current not set"}

    background_tasks.add_task(update, current)
    if use_html:
        encoded_string = construct_alert_parameters(
            type="success",
            title="Updating",
            text="Can take up to 30 seconds",
            timeout=6
        )
        return RedirectResponse(url=f"/?{encoded_string}", status_code=303)
    return {"status": "ok", "error": "none"}

@update_router.post("/previous")
async def previous(request: Request, background_tasks: BackgroundTasks):
    use_html = request.state.wants_html

    file_path = get_previous_image()
    if file_path is None:
        if use_html:
            encoded_string = construct_alert_parameters(
                type="error",
                title="No Previous Image",
                text="Unable to get the previous image",
                timeout=6
            )
            return RedirectResponse(url=f"/?{encoded_string}", status_code=303)
        return {"status": "error", "error": "unable to get next frame"}

    config.data.current_picture = str(file_path.resolve())
    await config.save()
    background_tasks.add_task(update, file_path)

    if use_html:
        encoded_string = construct_alert_parameters(
            type="success",
            title="Updating",
            text="Can take up to 30 seconds",
            timeout=6
        )
        return RedirectResponse(url=f"/?{encoded_string}", status_code=303)
    return {"status": "ok", "error": "none"}

@update_router.post("/next")
async def next(request: Request, background_tasks: BackgroundTasks):
    use_html = request.state.wants_html

    file_path = get_next_image()
    if file_path is None:
        if use_html:
            encoded_string = construct_alert_parameters(
                type="error",
                title="No Next Image",
                text="Unable to get the next image",
                timeout=6
            )
            return RedirectResponse(url=f"/?{encoded_string}", status_code=303)
        return {"status": "error", "error": "unable to get next frame"}

    config.data.current_picture = str(file_path.resolve())
    await config.save()
    background_tasks.add_task(update, file_path)

    if use_html:
        encoded_string = construct_alert_parameters(
            type="success",
            title="Updating",
            text="Can take up to 30 seconds",
            timeout=6
        )
        return RedirectResponse(url=f"/?{encoded_string}", status_code=303)
    return {"status": "ok", "error": "none"}

@app.get("/health")
async def health():
    return {"status": "ok", "error": "none"}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    images = sorted([f.name for f in pic_dir.glob("*.bmp")])
    name = ""
    if config.data.current_picture != "":
        name = Path(config.data.current_picture).name
    total, used, free = shutil.disk_usage("/")

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "images": images,
            "storage": {
                "total": f"{total / (10**9):.2f}",
                "used": f"{used / (10**9):.2f}",
                "free": f"{free / (10**9):.2f}"
            },
            "current": name,
            "interval": config.data.operation.interval,
            "start": config.data.operation.start,
            "mode": config.data.operation.mode,
            "timezone": datetime.now().astimezone().tzname()
        }
    )

@app.exception_handler(HardwareBusy)
async def hardware_busy_handler(request: Request, exc: HardwareBusy):
    if request.state.wants_html:
        encoded_string = construct_alert_parameters(
            type="message",
            title="Hardware Busy",
            text="Screen is refreshing, try again when it is done",
            timeout=6
        )
        return RedirectResponse(url=f"/?{encoded_string}", status_code=303)

    return JSONResponse(
        status_code=409,
        content={"status": "error", "error": "display is currently busy"},
    )

app.include_router(update_router)

if __name__ == "__main__":
    try:
        buttons.start_button_thread()
    except Exception as e: #noqa: BLE001
        logger.warning("no buttons found")

    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
