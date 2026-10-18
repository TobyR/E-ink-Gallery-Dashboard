from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import numpy as np

import argparse
import r_types

def get_palette(opts: r_types.ImageConvertOptions) -> np.ndarray:
    return r_types.PALETTES[opts.palette]

def get_pillow_palette(colours: np.ndarray) -> list[int]:
    palette = colours.astype(np.uint8).flatten().tolist()
    palette += [0, 0, 0] * (256 - 6)
    return palette

def dither_ordered(image, opts: r_types.ImageConvertOptions):
    colors = get_palette(opts).astype(np.float32)
    pixels = np.asarray(image, dtype=np.float32)

    # bayer matrix
    bayer = np.array([
        [ 0,  8,  2, 10],
        [12,  4, 14,  6],
        [ 3, 11,  1,  9],
        [15,  7, 13,  5],
    ], dtype=np.float32)

    bayer = (bayer + 0.5) / 16.0 - 0.5

    h, w = pixels.shape[:2]

    threshold = np.tile(
        bayer,
        (h // 4 + 1, w // 4 + 1)
    )[:h, :w]

    pixels = pixels + threshold[..., None] * 255 * opts.dither_strength

    diff = pixels[:, :, None, :] - colors[None, None, :, :]
    distance = np.sum(diff * diff, axis=3)

    indices = np.argmin(distance, axis=2).astype(np.uint8)

    result = Image.fromarray(indices, mode="P")
    result.putpalette(get_pillow_palette(colors))

    return result

def dither_floyd(image, opts: r_types.ImageConvertOptions):
    colors = get_palette(opts)

    palette_template = Image.new("P", (1, 1))
    palette_template.putpalette(get_pillow_palette(colors))

    image = image.quantize(palette=palette_template, dither=Image.Dither.FLOYDSTEINBERG)
    return image


def convert_to_bmp(image, opts: r_types.ImageConvertOptions):
    image = ImageOps.fit(image, (opts.width, opts.height), opts.resampling)
    image = image.convert("RGB")

    # Increase Saturation
    image = ImageEnhance.Color(image).enhance(opts.saturation)

    # Increase Contrast
    image = ImageEnhance.Contrast(image).enhance(opts.contrast)

    # Sharpen
    if opts.sharpness.percent > 0.0:
        image = image.filter(
            ImageFilter.UnsharpMask(
                radius=opts.sharpness.radius,
                percent=opts.sharpness.percent,
                threshold=opts.sharpness.threshold
            )
        )

    if opts.blur > 0.0:
        image = image.filter(ImageFilter.GaussianBlur(radius=opts.blur))

    match opts.dither_type:
        case r_types.DitherType.ORDERED:
            image = dither_ordered(image, opts)
        case r_types.DitherType.FLOYDSTEINBERG:
            image = dither_floyd(image, opts)

    return image


def process_file(input_path: Path, output_path: Path, opts: r_types.ImageConvertOptions):
    try:
        with Image.open(input_path) as image:
            result = convert_to_bmp(image, opts)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            result.save(output_path, format="BMP")

        print(f"Converted: {input_path} -> {output_path}")
        return True
    except Exception as exc:
        print(f"Failed: {input_path}: {exc}")
        return False

# input arguments
# 1 = input file or folder, 2 = output file or folder
def main():
    supported_files = [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"]

    parser = argparse.ArgumentParser(
        description="CLI tool to convert images to e-ink image"
    )

    parser.add_argument(
        "input",
        type=Path,
        help="Input image or folder"
    )

    parser.add_argument(
        "output",
        type=Path,
        help="Output image ot folder"
    )

    args = parser.parse_args()
    input_path: Path = args.input
    output_path: Path = args.output

    if not input_path.exists():
        parser.error(f"Input does not exist:: {input_path}")

    opts = r_types.default_ordered_options

    # single image input
    if input_path.is_file():
        if input_path.suffix.lower() not in supported_files:
            parser.error(f"Unsupported format: {input_path.suffix.lower}")

        is_output_folder = (
            output_path.is_dir or not output_path.suffix
        )

        if is_output_folder:
            output_path.mkdir(parents=True, exist_ok=True)
            output_file = output_path / f"{input_path.stem}.bmp"
        else:
            output_file = output_path

        success = process_file(input_path, output_file, opts)
        print(f"Finished: {input_path} - {success}")
        return

    if input_path.is_dir():
        if output_path.suffix and not output_path.is_dir:
            parser.error("Input is directory, output must be also")

        output_path.mkdir(parents=True, exist_ok=True)
        files = sorted(
            p for p in input_path.iterdir()
            if p.is_file()
            and p.suffix.lower() in supported_files
        )

        if not files:
            print(f"No supported images found in {input_path}")
            return

        successes = 0
        failures = []
        for file in files:
            output_file = output_path / f"{file.stem}.bmp"
            if process_file(file, output_file, opts):
                successes += 1
            else:
                failures.append(file)

        print(f"Finished: {successes}/{len(files)} converted")
        for file in failures:
            print(file)

if __name__ == "__main__":
    main()
