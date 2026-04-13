import docker


class DockerManager:
    def __init__(self) -> None:
        self.client = docker.from_env()
        self.images = self.client.images.list()

    def docker_pull(self, image: str) -> None:
        self.client.images.pull(f"nginx/{image}")
        print(f"Image '{image}' pulled successfully.")

    def docker_run(self, image: str) -> None:
        container = self.client.containers.run(image, detach=False)
        print(container.decode())
