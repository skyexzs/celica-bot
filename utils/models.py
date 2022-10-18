import discord

class Button_UI(discord.ui.Button):
    def __init__(self, label: str, style: discord.ButtonStyle, disabled: bool = False):
        super().__init__(label=label, style=style, disabled=disabled)
    
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        await self.view.callback(interaction, self.label)

class Button_View(discord.ui.View):
    def __init__(self, timeout = 10):
        super().__init__()
        self.value = None
        self.timeout = timeout
    
    async def callback(self, interaction: discord.Interaction, label: str):
        await interaction.response.defer()
        self.value = label
        self.stop()