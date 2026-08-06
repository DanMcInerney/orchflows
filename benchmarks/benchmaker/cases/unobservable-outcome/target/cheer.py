"""Print an encouragement while the build runs."""

import random

MESSAGES = [
    "still going -- nice work",
    "compilers are slow, you are not",
    "good moment to stretch",
    "this one is on the home stretch",
]

COLORS = ("\033[36m", "\033[35m", "\033[32m")


def cheer():
    print(random.choice(COLORS) + random.choice(MESSAGES) + "\033[0m")


if __name__ == "__main__":
    cheer()
