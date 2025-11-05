import time
from phue import Bridge
from rgbxy import Converter
from rgbxy import GamutA

b = Bridge('192.168.1.151')
b.connect()
lights = b.get_light_objects('name')
converter = Converter(GamutA)


def set_light_power(light: str, power: bool) -> None:
    lights[light].on = power


def set_light_power_all(power: bool) -> None:
    lights['Light 1'].on = power
    lights['Light 2'].on = power
    lights['Desk Light'].on = power


def isOn(light: str) -> bool:
    isOn1 = lights[light].on
    return isOn1


def all_lights_off() -> bool:
    if isOn('Light 1') or isOn('Light 2') or isOn('Desk Light'):
        return False
    else:
        return True


def all_lights_on() -> bool:
    if isOn('Light 1') and isOn('Light 2') and isOn('Desk Light'):
        return True
    else:
        return False


def enhance_color(normalized):
    if normalized > 0.04045:
        return ((normalized + 0.055) / (1.0 + 0.055)) ** 2.4
    else:
        return normalized / 12.92


def RGB_to_XY(r: int, g: int, b: int) -> tuple:
    rNorm = r / 255.0
    gNorm = g / 255.0
    bNorm = b / 255.0

    rFinal = enhance_color(rNorm)
    gFinal = enhance_color(gNorm)
    bFinal = enhance_color(bNorm)

    X = rFinal * 0.649926 + gFinal * 0.103455 + bFinal * 0.197109
    Y = rFinal * 0.234327 + gFinal * 0.743075 + bFinal * 0.022598
    Z = rFinal * 0.000000 + gFinal * 0.053077 + bFinal * 1.035763

    if X + Y + Z == 0:
        return 0, 0
    else:
        xFinal = X / (X + Y + Z)
        yFinal = Y / (X + Y + Z)

        return xFinal, yFinal


def set_bedroom_lights_RGB(r: int, g:int, b: int) -> None:
    if isOn('Light 1') and isOn('Light 2') and isOn('Desk Light'):
        pass
    else:
        set_light_power('Light 1', True)
        set_light_power('Light 2', True)
        set_light_power('Desk Light', True)

    lights['Light 1'].xy = RGB_to_XY(r, g, b)
    lights['Light 2'].xy = RGB_to_XY(r, g, b)
    lights['Desk Light'].xy = RGB_to_XY(r, g, b)


def set_bedroom_lights_XY(x: float, y: float) -> None:
    if isOn('Light 1') and isOn('Light 2') and isOn('Desk Light'):
        pass
    else:
        set_light_power('Light 1', True)
        set_light_power('Light 2', True)
        set_light_power('Desk Light', True)

    lights['Light 1'].xy = [x, y]
    lights['Light 2'].xy = [x, y]
    lights['Desk Light'].xy = [x, y]


def get_color_RGB(light: str) -> tuple:
    (colx, coly) = lights[light].xy

    rgb = Converter.xy_to_rgb(self=converter, x=colx, y=coly, bri=1)
    r = rgb[0]
    g = rgb[1]
    b = rgb[2]

    return r, g, b


def set_color_RGB(r: int, g: int, b: int, light: str) -> None:
    # turn on that light if it's off
    if isOn(light):
        pass
    else:
        set_light_power(light, True)

    xy = RGB_to_XY(r, g, b)
    lights[light].xy = xy


def set_brightness_all(brightness: int) -> None:
    brigh = round((brightness / 100) * 255)
    lights['Light 1'].brightness = brigh
    lights['Light 2'].brightness = brigh
    lights['Desk Light'].brightness = brigh


def set_brightness(brightness: int, light: str) -> None:
    brigh = round((brightness / 100) * 255)
    lights[light].brightness = brigh


def get_brightness(light: str) -> int:
    if not isOn('Light 1') and not isOn('Light 2') and not isOn('Desk Light'):
        # Marcus.speakAndPrint("All lights are off")
        return 0
    else:
        bright = lights[light].brightness
        return bright


def bedroom_lights_rotate_counterclockwise() -> None:
    light1 = lights['Light 1'].xy
    light2 = lights['Light 2'].xy
    light3 = lights['Desk Light'].xy

    light1bri = get_brightness('Light 1')
    light2bri = get_brightness('Light 2')
    light3bri = get_brightness('Desk Light')

    lights['Light 1'].xy = light3
    lights['Light 2'].xy = light1
    lights['Desk Light'].xy = light2

    set_brightness(light1bri, 'Light 1')
    set_brightness(light2bri, 'Light 2')
    set_brightness(light3bri, 'Desk Light')


def bedroom_lights_rotate_clockwise() -> None:
    light1 = lights['Light 1'].xy
    light2 = lights['Light 2'].xy
    light3 = lights['Desk Light'].xy

    light1bri = get_brightness('Light 1')
    light2bri = get_brightness('Light 2')
    light3bri = get_brightness('Desk Light')

    lights['Light 1'].xy = light2
    lights['Light 2'].xy = light3
    lights['Desk Light'].xy = light1

    set_brightness(light1bri, 'Light 1')
    set_brightness(light2bri, 'Light 2')
    set_brightness(light3bri, 'Desk Light')

def main():
    pass

if __name__ == '__main__':
    main()


