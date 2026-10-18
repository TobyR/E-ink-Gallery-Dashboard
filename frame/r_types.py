from dataclasses import field
from enum import IntEnum
from pydantic import BaseModel, Field, ConfigDict
from PIL import Image
import numpy as np

class OperationMode(IntEnum):
    STATIC = 0
    ROTATING = 1
    RANDOM = 2

class Operation(BaseModel):
    model_config = ConfigDict(use_enum_value=True)

    mode: OperationMode = Field(default=OperationMode.STATIC)
    start: str = Field(default="04:00")
    interval: int = Field(default=24, ge=1)

class DitherType(IntEnum):
    ORDERED = 0
    FLOYDSTEINBERG = 1

class ColourPalette(IntEnum):
    WAVESHARE_6COLOUR = 0

PALETTES = {
    ColourPalette.WAVESHARE_6COLOUR: np.array([
        [0, 0, 0],
        [255, 255, 255],
        [255, 255, 0],
        [255, 0, 0],
        [0, 255, 0],
        [0, 0, 255],
    ], dtype=np.uint8)
}

class SharpnessOptions(BaseModel):
    radius: float = Field(default=0.0)
    percent: int = Field(default=0)
    threshold: int = Field(default=0)

class ImageConvertOptions(BaseModel):
    width: int = Field(default=800)
    height: int = Field(default=480)

    dither_type: DitherType = field(default=DitherType.ORDERED)
    dither_strength: float = Field(default=1.0)

    palette: ColourPalette = Field(default=ColourPalette.WAVESHARE_6COLOUR)

    resampling: Image.Resampling = Field(default=Image.Resampling.LANCZOS)

    sharpness: SharpnessOptions = Field(default_factory=SharpnessOptions)
    saturation: float = Field(default=1.0)
    blur: float = Field(default=1.0)
    contrast: float = Field(default=1.0)

default_ordered_options = ImageConvertOptions(
    width=800,
    height=480,
    dither_type=DitherType.ORDERED,
    dither_strength=2.0,
    palette=ColourPalette.WAVESHARE_6COLOUR,
    resampling=Image.Resampling.LANCZOS,
    sharpness= SharpnessOptions(
        percent=20,
        radius=3.0,
        threshold=3
    ),
    saturation=2.0,
    blur=0.0,
    contrast=1.5
)

default_floyd_options = ImageConvertOptions(
    width=800,
    height=480,
    dither_type=DitherType.FLOYDSTEINBERG,
    dither_strength=2.0,
    palette=ColourPalette.WAVESHARE_6COLOUR,
    resampling=Image.Resampling.LANCZOS,
    sharpness= SharpnessOptions(),
    saturation=2.0,
    blur=0.0,
    contrast=1.5
)
