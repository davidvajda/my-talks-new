class Queue:
    class Node:
        def __init__(self, data):
            self.data = data
            self.next = None

    def __init__(self, values):
        self.front = self.rear = None
        [self.enqueue(value) for value in values]

    def enqueue(self, data):
        if self.is_empty():
            self.front = self.rear = self.Node(data)
        else:
            new_node = self.Node(data)
            self.rear.next = new_node
            self.rear = new_node

    def dequeue(self):
        node = self.front

        if not self.front:
            self.front = self.rear = None
            return None

        self.front = self.front.next
        return node.data

    def peek(self):
        if self.front:
            return self.front.data
        return None

    def is_empty(self):
        return False if self.front else True

if __name__ == "__main__":
    q = Queue(["hi", "my", "name", "is", "david"])
    
    while True:
        val = q.dequeue()
        print(val)
        if not val:
            break