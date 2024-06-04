# Townsquare Spy

This is a Python module to observe the townsquare app. It is intended to possibly be integrated with the bot, but isn't yet.

## Setup

1. Install a recent version of [Python](https://python.org/).
1. (Optional) Create a virtualenv to store dependencies. See [Python documentation](https://docs.python.org/3/library/venv.html) for how to do this.
1. Install requirements. `pip install -r requirements.txt`

## Usage

You can monitor an ongoing game from its URL.

```
python -m spy "https://clocktower.online/#game"
```

## Testing

The unit tests can be run by simply invoking `pytest`.

```
pytest
```