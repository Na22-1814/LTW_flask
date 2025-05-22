import cloudinary
import cloudinary.uploader
from flask import current_app
import os

def upload_image(file, folder='img'):
    """
    Upload an image to Cloudinary.
    
    Args:
        file: The file object to upload
        folder: The folder in Cloudinary to upload to
        
    Returns:
        dict: Cloudinary upload response or None if upload failed
    """
    try:
        if not file:
            return None
            
        # Upload the file to Cloudinary
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            use_filename=True,
            unique_filename=True
        )
        
        return result
    except Exception as e:
        current_app.logger.error(f"Error uploading to Cloudinary: {str(e)}")
        return None

def upload_file(file, folder='book_files'):
    """
    Upload a file (PDF) to Cloudinary.
    
    Args:
        file: The file object to upload
        folder: The folder in Cloudinary to upload to
        
    Returns:
        dict: Cloudinary upload response or None if upload failed
    """
    try:
        if not file:
            return None
            
        # Upload the file to Cloudinary
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type="raw",
            use_filename=True,
            unique_filename=True
        )
        
        return result
    except Exception as e:
        current_app.logger.error(f"Error uploading file to Cloudinary: {str(e)}")
        return None

def delete_asset(public_id):
    """
    Delete an asset from Cloudinary.
    
    Args:
        public_id: The public ID of the asset to delete
        
    Returns:
        dict: Cloudinary deletion response or None if deletion failed
    """
    try:
        if not public_id:
            return None
            
        # Delete the asset from Cloudinary
        result = cloudinary.uploader.destroy(public_id)
        
        return result
    except Exception as e:
        current_app.logger.error(f"Error deleting from Cloudinary: {str(e)}")
        return None