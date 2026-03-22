from dataclasses import dataclass, field


@dataclass
class ActionResult:
    success: bool
    message: str
    details: list = field(default_factory=list)  # log lines
    data: object = None                           # optional payload (e.g. pdf_path)


class BaseAction:
    name = ""
    description = ""

    def run(self, **kwargs) -> ActionResult:
        raise NotImplementedError
