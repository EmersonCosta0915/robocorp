import robo_log


def call_in_iterator(value):
    x = value


def create_iterator(steps: int):
    for step in range(steps):
        internal_value = step
        call_in_iterator(internal_value)
        robo_log.info("pause")
        yield internal_value
        robo_log.info("resume")


def call_in_main(value):
    y = value


def main():
    for entry in create_iterator(5):
        call_in_main(entry)
