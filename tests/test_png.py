from PIL import Image
import os
import urllib.request
from fastapi import APIRouter
from pims.formats import FORMATS
import io
from pims.importer.importer import FileImporter
from tests.utils.formats import info_test, thumb_test, resized_test, mask_test, crop_test, crop_null_annot_test, histogram_perimage_test
from pims.files.file import (
    EXTRACTED_DIR, HISTOGRAM_STEM, ORIGINAL_STEM, PROCESSED_DIR, Path,
    SPATIAL_STEM, UPLOAD_DIR_PREFIX
)
from pims.utils.strings import unique_name_generator
import pytest

def get_image(path, image):
	filepath = os.path.join(path, image)
	# If image does not exist locally -> download image
	
	if not os.path.exists(path):
		os.mkdir(path)
	
	if not os.path.exists(filepath):
		try:
			url = f"https://data.cytomine.coop/open/tests/{image}" #OAC
			urllib.request.urlretrieve(url, filepath)
		except Exception as e:
			print("Could not download image")
			print(e)
	
	if not os.path.exists(os.path.join(path, "processed")):
		try:
			fi = FileImporter(filepath)
			fi.upload_dir = f"{path}"
			fi.processed_dir = fi.upload_dir / Path("processed")
			fi.mkdir(fi.processed_dir)
		except Exception as e:
			print(path + "processed could not be created")
			print(e)

	if not os.path.exists(os.path.join(path, "processed/visualisation.PNG")):
		try:
			fi.upload_path = Path(filepath)
			original_filename = Path(f"{ORIGINAL_STEM}.PNG")
			fi.original_path = fi.processed_dir / original_filename
			fi.mksymlink(fi.original_path, fi.upload_path)
			spatial_filename = Path(f"{SPATIAL_STEM}.PNG")
			fi.spatial_path = fi.processed_dir / spatial_filename
			fi.mksymlink(fi.spatial_path, fi.original_path)
		except Exception as e:
			print("Importation of images could not be done")
			print(e)
			
def test_png_exists(image_path_png):
	get_image(image_path_png[0], image_path_png[1])
	assert os.path.exists(os.path.join(image_path_png[0],image_path_png[1])) == True
	
def test_png_info(client, image_path_png):
	info_test(client, image_path_png[1], "png")
	
def test_png_norm_tile(client, image_path_png):
	response = client.get(f"/image/upload_test_png/{image_path_png[1]}/normalized-tile/zoom/1/ti/0", headers={"accept": "image/jpeg"})
	assert response.status_code == 200
	
	img_response = Image.open(io.BytesIO(response.content))
	width_resp, height_resp = img_response.size
	assert width_resp == 256
	assert height_resp == 79
	
def test_png_thumb(client, image_path_png):
	thumb_test(client, image_path_png[1], "png")
	
def test_png_resized(client, image_path_png):
	resized_test(client, image_path_png[1], "png")
	
def test_png_mask(client, image_path_png):
	mask_test(client, image_path_png[1], "png")
	
def test_png_crop(client, image_path_png):
	crop_test(client, image_path_png[1], "png")
	
@pytest.mark.skip()
def test_png_crop_null_annot(client, image_path_png):
	crop_null_annot_test(client, image_path_png[1], "png")

@pytest.mark.skip
def test_png_histogram_perimage(client, image_path_png):
	histogram_perimage_test(client, image_path_png[1], "png")
