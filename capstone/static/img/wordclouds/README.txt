Thumbnail creation, run in this dir:

mogrify -path thumbs -thumbnail 200x200 *.png
pngquant --ext .png --force thumbs/*.png