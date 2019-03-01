from component import BaseConfigHandler
from component import BaseConfigComponentFactory

class ReportEncoderFactory(BaseConfigComponentFactory):
    def __init__(self, component_name):
        super().__init__(ReportEncoderConfigHander(component_name))

    def create_component(self, config, context=None):
        return ReportEncoder(BaseConfigHandler(config))
    