import utime
import math


def ease_in_out_sine(x, start, end, duration):
    return -(end - start) / 2 * (math.cos(math.pi * x / duration) - 1) + start


def float_range(start, end, num_steps):
    step = (end - start) / (num_steps - 1)
    return [ease_in_out_sine(i * step + start, start, end, num_steps * step) for i in range(num_steps)]


class SmoothServo:

    NUMBER_OF_STEPS = 100

    def __init__(self, servo):
        self.servo = servo
        self.target = None

    def _degree_2_rad(self, degree):
        rad = math.radians(degree)
        us = rad * self.servo._slope + self.servo._offset
        return us

    def run(self):
        while True:
            if not self.target:
                utime.sleep_ms(100)
                continue
            target_us = self._degree_2_rad(self.target)
            self.target = None
            for us in float_range(self.servo.read_us(), target_us, self.NUMBER_OF_STEPS):
                self.servo.write_us(us)
                if self.target:
                    break
                utime.sleep_ms(1)
            if not self.target:
                self.servo.write_us(target_us)
