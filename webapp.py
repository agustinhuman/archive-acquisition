import base64
import csv
import os
from pathlib import Path
import hashlib

from fastapi import FastAPI
from pydantic import BaseModel
from starlette.responses import HTMLResponse

from context import get_app_context
from preprocessors import Rotate

app = FastAPI()

class ImageData(BaseModel):
    image_data: str  # Base64
    image_name: str  # Human name

class ImageWithMetadata(BaseModel):
    metadata: dict[str, str]

class ImageTransformRequest(BaseModel):
    """Request for an image transformation, withouth retakng the image itself.

    It describe a known trnasformation and the parameters to apply it."""
    transformation: str  # Name of the transformation
    parameters: dict[str, str]

@app.get("/", response_class=HTMLResponse)
def get_webapp():
    return open("index.html").read()


def get_image_base64(photo: bytes, human_name=None) -> ImageData:
    """Get the image as base64 and its name"""

    # Read the image file and encode it as base64
    encoded_image = base64.b64encode(photo).decode('utf-8')
    mime_type = 'image/jpeg'  # Default to JPEG

    # Return the base64 encoded image with its data URL prefix and the image name
    return ImageData(
        image_data = f'data:{mime_type};base64,{encoded_image}',
        image_name = human_name or "photo",
    )

@app.get('/get_image')
def get_image() -> ImageData:
    """Takes a photo and returns a JSON with a base64 encoded image (image_data),
    the name of the image (image_name) and the hash of the image (hash)"""
    ctx = get_app_context()
    photo = ctx.provider.take_photo()
    processed = ctx.preprocessor(photo).run()
    rotated = Rotate(processed, ctx.last_rotation).run()
    ctx.last_image_raw = photo
    ctx.last_image_processed = rotated
    image_data = get_image_base64(rotated, "base_processed")
    return image_data

@app.post('/transform_image')
def transform_image(transformation: ImageTransformRequest) -> ImageData:
    """Request for the last image to be transformed.

    It receives the hash of the image (to double check), a known transformation name and some optional parameters.
    Example usage

    Rotate 90  # Will rotate the image 90 degrees clockwise
    Rotate 180  # Will rotate the image 180 degrees
    Rotate 270  # Will rotate the image 90 degrees counterclockwise
    Raw  # Request for the original image without any transformation
    """
    # Apply the requested transformation
    ctx = get_app_context()
    if transformation.transformation == "Rotate":
        angle = int(transformation.parameters.get("angle", "0"))
        ctx.last_rotation = (ctx.last_rotation + angle) % 360
        ctx.last_image_processed = Rotate(ctx.last_image_processed, angle).run()
        return get_image_base64(ctx.last_image_processed, f"Rotated {angle}")
    elif transformation.transformation == "Raw":
        # Return the original image
        ctx.last_image_processed = ctx.last_image_raw
        return get_image_base64(get_app_context().last_image_raw, "Raw")
    else:
        raise ValueError(f"Unknown transformation: {transformation.transformation}")

@app.post('/submit')
def submit(data: ImageWithMetadata):
    """Receives the metadata the user has entered and saves it to a CSV file."""
    ctx = get_app_context()
    ctx.exporter.export(ctx.last_image_processed, data.metadata)
