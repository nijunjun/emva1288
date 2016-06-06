import numpy as np
from emva1288.camera import Camera
from emva1288.process.routines import get_int_imgs
from emva1288 import process


def get_emva_blackoffset(cam):
    """Find the blackoffset to satifsfy EMVA1288 requirements"""
    bini = c.blackoffset
    # Find black offset with a maximum of 0.5% of values at Zero
    bo = cam.blackoffsets[0]
    pixels = cam.img_x * cam.img_y
    for i in cam.blackoffsets:
        cam.blackoffset = i
        img = cam.grab()
        if np.count_nonzero(img) > pixels * .995:
            break
        bo = i
    cam.blackoffset = bini
    return bo


def get_emva_gain(cam):
    """Find the gain to satisfy EMVA1288 requirements"""
    gini = c.K
    # Find gain with a minum temporal noise of 0.5DN
    g = cam.Ks[0]
    for gain in cam.Ks:
        cam.gain = gain
        img1 = cam.grab()
        img2 = cam.grab()
        if (img1 - img2).std() > 0.5:
            break
        g = gain
    c.K = gini
    return g


def get_temporal(cam, illumination):
    img1 = cam.grab()
    img2 = cam.grab()
    imgs = get_int_imgs((img1, img2))
    value = {'sum': np.sum(imgs['sum']), 'pvar': np.sum(imgs['pvar'])}
    if illumination == 'bright':
        return {cam.get_photons(): value}
    return value


def get_spatial(cam, illumination, L=50):
    imgs = []
    for i in range(L):
        imgs.append(cam.grab())
    value = get_int_imgs(imgs)
    if illumination == 'bright':
        return {cam.get_photons(): value}
    return value


data = {'version': None,
        'format': {},  # bits, witdth, height
        'name': None,
        'info': {},
        'temporal': {'dark': {}, 'bright': {}},
        'spatial': {'dark': {}, 'bright': {}},
        }


# Intialize the camera, here we can specify different image size
# or any other parameter that Camera allows
c = Camera(bit_depth=10,
           img_x=100,
           img_y=50)

# Fill the information
data['format'] = {'bits': c.bit_depth,
                  'width': c.img_x,
                  'height': c.img_y}

# Maximum exposure for test
exposure_max = 9000000

# Go to darkness
c.set_radiance(0)

# Find the camera parameters for the test
c.exposure = exposure_max
c.blackoffset = get_emva_blackoffset(c)
c.K = get_emva_gain(c)

# Find the radiance that will saturate the camera at our maximum exposure time
saturation_radiance = c.get_radiance_for()

exposure_spatial = None
for illumination in ('bright', 'dark'):
    if illumination == 'bright':
        c.set_radiance(saturation_radiance)
    else:
        c.set_radiance(0)

    for exposure in np.linspace(c.exposure_min, exposure_max, 100):
        c.exposure = exposure

        data['temporal'][illumination][exposure] = get_temporal(c,
                                                                illumination)

        img = c.grab()
        if not exposure_spatial and (img.mean() > c.img_max / 2.):
            exposure_spatial = exposure

        if exposure_spatial == exposure:
            data['spatial'][illumination][exposure] = get_spatial(c,
                                                                  illumination)
        print(exposure, img.mean(), img.std())

# Process the collected data
dat = process.Data1288(data)
res = process.Results1288(dat)
res.print_results()
# plot = process.Plotting1288(res)
# plot.plot()
