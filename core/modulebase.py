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
    
    @staticmethod
    def config_required() -> list[str]:
        """
        Returns a list of config paths which need to exist for the module to be loaded
        """
        return []
    
    def __str__(self):
        return f"{self.name()} Module, requires config: [{"".join(self.config_required)}]"