class DockerImage:
    def __init__(self, id, timestamp, actor, host, address, repository, tag) -> None:
        self.id = id
        self.timestamp = timestamp
        self.actor = actor
        self.host = host
        self.address = address
        self.repository = repository
        self.tag = tag

    def __str__(self) -> str:
        return f"""
            Id: {self.id}
            Timestamp: {self.timestamp}
            Actor: {self.actor}
            Host: {self.host}
            Address: {self.address}
            Repository: {self.repository}
            Tag: {self.tag}
        """
