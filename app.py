from monai.networks.nets import DenseNet121
import torch
import os
from torch.utils.data import DataLoader
from flask import Flask, jsonify, request
import json
from monai.transforms import LoadImage, Resize, NormalizeIntensity,RandRotate,RandFlip,RandZoom,Compose,Activations, AsDiscrete,EnsureChannelFirst,ToTensor,AddChannel
from pydicom.filebase import DicomBytesIO
from pydicom import dcmread
app = Flask(__name__)

transforms = Compose([LoadImage(image_only=True,reader="PydicomReader"),EnsureChannelFirst() ,NormalizeIntensity(),Resize((256,256))])
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = DenseNet121(spatial_dims=2, in_channels=1, out_channels=2).to(device)
root_dir = "./model_weight/"
model.load_state_dict(torch.load(os.path.join(root_dir, "best_metric_model.pth"), map_location=torch.device('cpu') if not torch.cuda.is_available() else None))
model.eval()
transforms = Compose([AddChannel(),NormalizeIntensity(),Resize((256,256))])


class BrainClassificationDatasetinference(torch.utils.data.Dataset):
    def __init__(self, image_files, transforms):
        self.image_files = image_files
        
        self.transforms = transforms

    def __len__(self):
        return len(self.image_files)

    def __getitem__(self, index):
        return self.transforms(self.image_files[index])

    
def get_dataset(image_file):
    raw_bytes = DicomBytesIO(image_file.read())
    return dcmread(raw_bytes)


def get_prediction(test_images):
    test_images = transforms(test_images)
    with torch.no_grad():
        test_images = test_images.unsqueeze(0).to(device)
        pred = model(test_images).argmax(dim=1)
    return pred.item()    


@app.route('/predict', methods=['POST'])
def predict():
    """Run brain vs. non-brain classification on one or multiple DICOM images"""

    if request.method == 'POST':
        # Can supply one or multiple DICOM images (as binary files)
        # all with the same the parameter name "file"
        files = request.files.getlist("file")

        # The API returns a list of dicts containing predictions,
        # one dict for each input DICOM image
        predictions = []

        for file in files:
            prediction = {k: None for k in ("series_instance_uid", "sop_instance_uid", "prediction")}
            try:
                ds = get_dataset(file)
                prediction["series_instance_uid"] = ds.SeriesInstanceUID
                prediction["sop_instance_uid"] = ds.SOPInstanceUID

                class_name = get_prediction(ds.pixel_array)
                prediction["prediction"] = class_name
            except Exception as ex:
                # TODO: if any one the files cannot be read/predicted,
                # should we return HTTP status code != 200?
                prediction["error_msg"] = str(ex)
            finally:
                predictions.append(prediction)

        return jsonify(predictions)


if __name__ == '__main__':
    app.run()
