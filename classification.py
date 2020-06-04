from edgetpu.classification.engine import ClassificationEngine
from edgetpu.utils import dataset_utils
from PIL import Image
from threading import Thread, Event
from queue import Queue, Empty


import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Classify(object):
    """Save image to file"""

    def __init__(self):

        logger.info("Initialising classifier...")

        self.classifiers = {}

        self.quit_event = Event()
        self.file_queue = Queue()
        self.data = None

        self.load_classifiers("pasta", "sauce", "pan_on_off")

    def _worker(self):

        logger.debug("Initialising classification worker")

        while True:
            try:  # Timeout raises queue.Empty

                image = self.file_queue.get(block=True, timeout=0.1)
                image = Image.open(image)

                output = {}

                for name, c in self.classifiers.items():

                    logger.debug("Starting classifier %s " % (name))

                    engine = c["model"]
                    labels = c["labels"]

                    result = engine.classify_with_image(image, top_k=1)
                    logger.debug(result)

                    try:
                        result = result[0]
                        output[name] = {
                            "label": labels[result[0]],
                            "confidence": str(result[1]),
                        }
                    except TypeError:
                        logger.debug("TypeError")
                    except IndexError:
                        logger.debug("IndexError")
                logger.debug(output)
                self.data = output
                self.file_queue.task_done()

            except Empty:
                if self.quit_event.is_set():
                    logger.debug("Quitting thread...")
                    break

    def load_classifiers(self, classifiers):

        available_classifiers = {
            "pasta": {"labels": "models/pasta.txt", "model": "models/pasta.tflite"},
            "sauce": {"labels": "models/sauce.txt", "model": "models/sauce.tflite"},
            "pan_on_off": {
                "labels": "models/pan_on_off.txt",
                "model": "models/pan_on_off.tflite"
            },
        }

        for name in classifiers:
            if name not in self.classifiers:
                try:
                    attributes = available_classifiers[name]
                    output = {}
                    output["labels"] = dataset_utils.read_label_file(attributes["labels"])
                    output["model"] = ClassificationEngine(attributes["model"])
                    self.classifiers[name] = output
                except KeyError:
                    raise KeyError("Model name not found in database")
                except FileNotFoundError:
                    raise FileNotFoundError("Model or labels not found in models folder")

    def start(self, file_path):
        logger.debug("Calling start")
        self.file_queue.put(file_path)

    def join(self):
        logger.debug("Calling join")
        self.file_queue.join()

    def launch(self):
        logger.debug("Initialising classification worker")
        self.thread = Thread(target=self._worker, daemon=True)
        self.thread.start()

    def quit(self):
        self.quit_event.set()
        logger.debug("Waiting for classification thread to finish")
        self.thread.join()
