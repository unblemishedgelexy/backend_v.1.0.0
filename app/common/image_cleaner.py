from PIL import Image

def clean_image(input_path, output_path, quality=85):
    with Image.open(input_path) as img:
        data = list(img.getdata())
        clean = Image.new(img.mode, img.size)
        clean.putdata(data)

        clean.save(
            output_path,
            optimize=True,
            quality=quality
        )

    return output_path
