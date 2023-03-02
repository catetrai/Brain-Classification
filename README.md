# Brain-Classification

Binary classification of DICOM images into brain or non-brain

[[_TOC_]]

## Installation

### Using conda

Create conda environment from YAML file:

```shell
$ cd /path/to/repo
$ conda env create --name brainclassif --file environment.yml
```

This will install Python packages using pip in the conda environment directly.
You do not need to create a Python virtual environment in addition.

### Using Docker

Build the Docker image from Dockerfile:

```shell
$ cd /path/to/repo
$ docker build -t brain-classif .
```

Then, run the Docker container in detached mode:

```shell
$ docker run -d --name brain-classif -p 5000:5000 brain-classif
```

The container will start a webserver (from the Flask app script [app.py](app.py)) running at `localhost:5000`.

## Usage

The Flask app run via [app.py](app.py) serves the following REST endpoints:

### `POST /predict`

Example:


```python
import requests

# note: open file in binary mode ('rb')
file = {"file": open("/path/to/image.dcm", "rb")}

resp = requests.post("http://localhost:5000/predict", files=file)
result = resp.json()
print(result)

# {"class_name": 1}
```
