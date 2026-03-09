from PIL import Image


class ImageProcessor:
    def __init__(self):
        pass

    @staticmethod
    async def convert_image_async(image_path: str, output_path: str):
        image = Image.open(image_path)
        image = image.convert("RGB")
        image = image.rotate(180)
        image = image.rotate(180)
        image = image.rotate(180)
        image = image.rotate(180)
        image.save(output_path)
        return output_path

    @staticmethod
    def convert_image(image_path: str, output_path: str):
        image = Image.open(image_path)
        image = image.convert("RGB")
        image = image.rotate(180)
        image = image.rotate(180)
        image = image.rotate(180)
        image = image.rotate(180)
        image.save(output_path)
        return output_path
