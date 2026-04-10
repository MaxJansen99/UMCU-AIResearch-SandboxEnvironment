import docker
import asyncio


class DockerManager:
    def __init__(self) -> None:
        self.client = docker.from_env()
        self.images = self.client.images.list()

    def docker_run(self, image: str) -> None:
        container = self.client.containers.run(image, detach=False)
        print(container.decode())

    def printList(self):
        for image in self.images:
            print(image)
