import json, asyncio, logging
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError

from r_types import Operation

logger = logging.getLogger(__name__)

class ConfigModel(BaseModel):
    current_picture: str = Field(default="")
    next_update: int = Field(default=0)
    operation: Operation = Field(default_factory=Operation)


class Config:
    def __init__(self, path: Path):
        self.path: Path = path
        self.backup_path: Path = path.with_suffix(path.suffix + ".bak")
        self.lock: asyncio.Lock = asyncio.Lock()
        
        self.data: ConfigModel = ConfigModel()

    # save and load are async so we need an async create method
    @classmethod
    async def create(cls, path: Path) -> "Config":
        instance = cls(path)
        await instance.load()
        return instance

    async def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if self.path.exists():
            try:
                with self.path.open("r", encoding="utf-8") as f:
                    json.load(f)  # Validate that it's valid JSON.

                self.path.replace(self.backup_path)
            except (json.JSONDecodeError, OSError) as e:
                logger.error(f"Error saving to file: {e}")

        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp_path.touch()

        try:
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(self.data.model_dump(mode="json"), f, indent=4)
                f.write("\n")

            tmp_path.replace(self.path)
        except Exception as e:
            if tmp_path.exists():
                tmp_path.unlink()
            raise OSError(f"Failed to save configuration: {e}") from e

        
    async def save(self):
        async with self.lock:
            await self._save()

    async def _load(self):
        if self.path.exists():
            try:
                with self.path.open("r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                    self.data = ConfigModel.model_validate(raw_data)
                    return
            except (json.JSONDecodeError, OSError, ValidationError) as e:
                logger.debug(f"Loading exising config error: {e}")

        if self.backup_path.exists():
            try:
                with self.backup_path.open("r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                    self.data = ConfigModel.model_validate(raw_data)

                    tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")

                    with tmp_path.open("w", encoding="utf-8") as f:
                        json.dump(self.data.model_dump(), f, indent=4)
                        f.write("\n")

                    tmp_path.replace(self.path)
                    return
            except (json.JSONDecodeError, OSError, ValidationError) as e:
                logger.warning(f"Loading exising backup config error: {e}")

        # Cant load file or backup
        self.data = ConfigModel()


    async def load(self):
        async with self.lock:
            await self._load()
        await self.save()
