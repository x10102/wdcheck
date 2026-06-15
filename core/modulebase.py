from discord import Cog

class ModuleBase(Cog):
    
    @staticmethod
    def env_override() -> str:
        return ""
    
    @staticmethod
    def name() -> str:
        return "Base Module"