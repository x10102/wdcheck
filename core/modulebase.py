from discord import Cog

class ModuleBase(Cog):
    
    @staticmethod
    def env_override() -> str:
        """
        Returns the name of the environment variable that will prevent the module from loading if set to 'true'
        """
        return ""
    
    @staticmethod
    def name() -> str:
        """
        Returns the name of the module to be displayed in logs
        """
        return "Base Module"