# E-ink Gallery Dashboard
Easy to use dashboard gallery for e-ink displays, uses fastapi to control the display. Only used with a 7.3" Waveshare 6-color (e) display with a Raspberry Pi Zero W. main.py can still be run on a non pi device to test the UI and webserver.

Please note this is just a small personal project as I wanted to build my own e-ink display and likely wont respond to issues

## Features
- Easily upload a picture to the device
- Ability to cycle through gallery randomly or in an order at certain times
- Has button integration to select the next or previous image

## TODO
- Add advanced image upload menu for batch image uploads or ImageConvertOptions settings
- Optimize each ImageConvertOption defaults for both Floyd-Steinberg and ordered "Bayer" dithering. 


## Requirements
Only Tested with a Raspberry Pi Zero W
```
sudo apt install python3-fastapi, python3-uvicorn, python3-numpy, python3-pil, python3-dotenv, python3-gpiozero
```

## Installation
Once requirements are installed, clone repo to device and run the install script. Everything is installed and run as root/sudo. You can run main.py first before installing and change the .env file if required

The install script does the following:
1. Copies frame/ and trigger/ into /opt/ (ignoring config.json)
2. Copies services/ into /etc/systemd/system/
3. Enables and starts the services

## Other Information
### convert.py
Can be run by itself to batch convert images if prefered. You need to supply an input and output, output should be .bmp
```
sudo python3 convert.py "image.jpg" "image.bmp"
```
or you can supply a directory to output to a directory
```
sudo python3 convert.py "images/" "output/"
```

### buttons.py
Can also be run by itself to test the buttons with the gpio
