import abc
import logging
import tempfile
from pathlib import Path

import cv2
import imutils
import numpy as np
from cv2 import Mat
from imutils.perspective import four_point_transform

class Preprocessor(abc.ABC):
    def __init__(self, image_bytes: bytes):
        self.raw_image: bytes = image_bytes

    def run(self) -> bytes | None:
        try:
            return self._preprocess()
        except Exception as e:
            logging.error(f"Error taking photo: {e}")
            return None

    @abc.abstractmethod
    def _preprocess(self) -> bytes:
        """Preprocess the image"""

class PreprocessorComposite(Preprocessor):
    def __init__(self, image_path, preprocessors: list[type[Preprocessor]]):
        super().__init__(image_path)
        self.preprocessors = preprocessors

    def _preprocess(self) -> bytes:
        for preprocessor in self.preprocessors:
            self.raw_image = preprocessor(self.raw_image ).run()
        return self.raw_image


def get_image_matrix_from_bytes(image_bytes: bytes) -> np.ndarray:
    image = np.asarray(bytearray(image_bytes), dtype="uint8")
    return cv2.imdecode(image, cv2.IMREAD_COLOR)

class ExtractDocument(Preprocessor):
    """Cuts and project the document from the image.

    Based on:
    https://pyimagesearch.com/2014/09/01/build-kick-ass-mobile-document-scanner-just-5-minutes/
    """

    def __init__(self, image_bytes):
        super().__init__(image_bytes)

        self.image = get_image_matrix_from_bytes(image_bytes)
        self.original_image = self.image.copy()

        # Detected contours on the image (Scaled)
        self.contours = None
        # Ration of the scaled image with respect to the original size
        self.ratio = 1

        # Copy of the image as it's transformed. Used for debugging.
        self.transformations: {str: Mat} = {}

    def simplify(self):
        """Loads an image and simplifies it"""
        self.ratio = self.image.shape[0] / 500.0
        image = imutils.resize(self.image, height = 500)
        # convert the image to grayscale, blur it and find edges
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(gray, 75, 200)
        self.image = edged
        self.transformations["simplified"] = edged.copy()

    def _preprocess(self) -> bytes:
        self.simplify()
        self.detect_contours()
        self.project()
        self.draw_on_image()
        return cv2.imencode('.jpg', self.image)[1].tobytes()

    def detect_contours(self):
        contours = cv2.findContours(self.image.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = imutils.grab_contours(contours)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

        document_contour = None
        for contour in contours:
            # approximate the contour
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            # if our approximated contour has four points, then we
            # can assume that we have found our screen
            if len(approx) == 4:
                document_contour = approx
                break

        if document_contour is None:
            raise Exception("Could not find document contour")

        self.contours = document_contour

        self.image = document_contour
        self.transformations["contours"] = document_contour.copy()


    def project(self):
        self.image = four_point_transform(self.original_image, self.contours.reshape(4, 2) * self.ratio)
        self.transformations["projected"] = self.image.copy()

    def draw_on_image(self):
        image_drawn = self.original_image.copy()
        cv2.drawContours(image_drawn, [(self.contours.reshape(4, 1, 2) * self.ratio).astype(dtype=np.dtypes.Int32DType)], -1, (0, 0, 255), 8)
        self.transformations["drawn"] = image_drawn.copy()

class Rotate(Preprocessor):

    def __init__(self, image_bytes, angle: int = 0):
        super().__init__(image_bytes)
        if angle not in [0, 90, 180, 270]:
            raise Exception("Angle must be one of 0, 90, 180, 270")
        self.angle = angle

    def _preprocess(self) -> bytes:
        if self.angle == 0:
            return self.raw_image

        image = get_image_matrix_from_bytes(self.raw_image)
        if self.angle == 180:
            image = cv2.rotate(image, cv2.ROTATE_180)
        elif self.angle == 90:
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif self.angle == 270:
            image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)

        return cv2.imencode('.jpg', image)[1].tobytes()

if __name__ == '__main__':
    image = Path("photo.jpg")
    ExtractDocument(image.read_bytes()).run()
