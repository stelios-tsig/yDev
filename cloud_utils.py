import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv


#Reading from env
load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

def upload_image_to_cloudinary(file,public_id: str) -> str:
    result = cloudinary.uploader.upload(file, public_id= public_id, overwrite= True)
    return result["secure_url"]