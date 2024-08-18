from multiprocessing import Lock, Manager, RLock


class Vocabulary:

    def __init__(self, thread_safe=False):

        if thread_safe:
            self.mutex = Lock()
            manager = Manager()

            self.vocabulary = manager.dict({
                "character": -2
            })
            self.i_vocabulary = manager.dict({
                -2: "character"
            })
        else:
            self.vocabulary = {
                "character": -2
            }
            self.i_vocabulary = {
                -2: "character"
            }
            self.mutex = None

    def _get_vocabulary(self):
        return self.vocabulary, self.i_vocabulary

    def _update_vocabulary(self, item):
        """
        Including a mutex to ensure that the vocabulary is managed in a threadsafe way.
        Otherwise, two processes may allocate different items to the same index.
        """
        if self.mutex:
            try:
                with self.mutex:
                    keys = self.vocabulary.keys()
                    next_index = len(keys)
                    if item not in keys:
                        self.vocabulary[item] = next_index
                        self.i_vocabulary[next_index] = item
                        #print(f"vocab: {item} = {next_index}")

                item = self.vocabulary[item]
            except Exception as e:
                print(e)
        else:
            keys = self.vocabulary.keys()
            next_index = len(keys)
            if item not in keys:
                self.vocabulary[item] = next_index
                self.i_vocabulary[next_index] = item
                #print(f"vocab: {item} = {next_index}")

            item = self.vocabulary[item]
        return item