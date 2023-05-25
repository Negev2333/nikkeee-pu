import discord
from discord.ext import commands

'''
TODO:
功能:
1. 存檔功能，避免斷線重開資料消失
2. 
3. (low priority) 產生 excel 報表

refactor:
1. 血量管理的部分寫成一個 class
2. 前項改完後，"指令部分"內部不得做資料處哩，全部都只能呼叫前一項的 function

'''

# 設定prefix與權限
client = commands.Bot(command_prefix="!", intents=discord.Intents().all())

# 變數初始值
boss_reports = {}
current_round = 1
boss_hp = [100, 100, 100, 100, 100]


# ======================================================================================================================
#  資料類別
# ======================================================================================================================

class Data:
    cmd_list = [
        "**!menu** - 叫出互動式選單",
        "**!sign** - 預訂要刀幾王",
        "**!attack (王) (血量)** - 填寫出刀傷害",
        "**!list** - 顯示本階段刀表",
        "**!now** - 查詢現在進度",
        "**!command** - 其他選項",
        "**!health (,分開)** - 設定王的血量(預設100)",
        "**!clear** - 清除刀表",
        "**!phase** (階段數) - 切換階段",
        "**!reset** - 重置刀表",
    ]


# ======================================================================================================================
#  類別定義
# ======================================================================================================================

# 選單
class Select(discord.ui.Select):
    def get_ops(self):
        return [
            {"label": "報刀",     "emoji": "🗳️", "desc": "預訂要刀幾王",   "func": self.報刀},
            {"label": "出刀",     "emoji": "🗡️", "desc": "填寫出刀傷害",   "func": self.出刀},
            {"label": "列出刀表",  "emoji": "📃", "desc": "顯示本階段刀表", "func": self.列出刀表},
            {"label": "進度",     "emoji": "🏆", "desc": "查詢現在進度",   "func": self.進度},
            {"label": "指令",     "emoji": "⚙️", "desc": "其他選項",      "func": self.指令},
        ]

    def __init__(self):
        options = [
            discord.SelectOption(label=op["label"], emoji=op["emoji"], description=op["desc"])
            for op in self.get_ops()
        ]
        super().__init__(placeholder="請選擇", max_values=1, min_values=1, options=options)

    # 選項回傳
    async def callback(self, interaction: discord.Interaction):
        for op in self.get_ops():
            if self.values[0] == op['label']:
                await op['func'](interaction)
                return

    async def 報刀(self, interaction: discord.Interaction):
        await interaction.response.send_message("請選擇要刀的王", ephemeral=True, view=SelectBossView())

    async def 出刀(self, interaction: discord.Interaction):
        await send_msg(interaction, title="請使用指令 `!sign 王 血量` 來輸入血量")

    async def 列出刀表(self, interaction: discord.Interaction):
        await send_msg(interaction, title=generate_report())

    async def 進度(self, interaction: discord.Interaction):
        await send_msg(interaction, title=check_boss_health())

    async def 指令(self, interaction: discord.Interaction):
        await send_msg(interaction, title="指令列表", description="\n".join(Data.cmd_list))


# 選單待機
class SelectView(discord.ui.View):
    def __init__(self, *, timeout=600):
        super().__init__(timeout=timeout)
        self.add_item(Select())


# 選擇王 按鈕
class SelectBossView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=600)
        for i in range(5):
            self.add_item(SelectBossButton(i + 1))


# 選擇王 結果
class SelectBossButton(discord.ui.Button):
    def __init__(self, boss_number):
        super().__init__(style=discord.ButtonStyle.primary, label=f"{boss_number}王", custom_id=f"boss_{boss_number}")

    async def callback(self, interaction: discord.Interaction):
        boss_number = int(self.custom_id.split('_')[1])
        if interaction.message.content.startswith("請選擇要刀的王"):
            await send_msg(interaction, title=f"已成功報刀：第 {current_round} 階 {boss_number} 王", ephemeral=False)
            add_boss_report(current_round, boss_number, "新增", interaction.user)


# ======================================================================================================================
#  刀表 func
# ======================================================================================================================

# 編輯刀表
def add_boss_report(round_number, boss_number, action, member):
    boss_reports.setdefault(round_number, {}).setdefault(boss_number, [])
    if action == "新增":
        name = member.nick or member.name
        boss_reports[round_number][boss_number].append(name)
    elif action == "刪除":
        name = member.nick or member.name
        if name in boss_reports[round_number][boss_number]:
            boss_reports[round_number][boss_number].remove(name)


# 清除刀表 (單隻王)
def clear_single_boss_report(boss_number):
    for reports in boss_reports.values():
        reports.pop(boss_number, None)


# 清除刀表
def clear_boss_reports():
    boss_reports.clear()


# 列出刀表
def generate_report():
    if not boss_hp:
        return "血量尚未設定"

    if not boss_reports or not boss_reports.get(current_round):
        return "尚未有任何排刀"

    report = ""
    report += f"**第 {current_round} 階**\n"
    for boss_number in range(1, 6):
        if boss_number > len(boss_hp):
            break
        if boss_hp[boss_number - 1] <= 0:
            boss_hp_text = "已消滅"
        else:
            boss_hp_text = str(boss_hp[boss_number - 1])
        report += f"{boss_number}王 ({boss_hp_text}): "
        members = boss_reports[current_round].get(boss_number, [])
        if members:
            report += ", ".join(members)
        report += "\n"
    return report


# 進入下輪
def next_round():
    global current_round
    if current_round == 10:
        clear_boss_reports()
        current_round = 1
    else:
        current_round += 1
        clear_boss_reports()
    boss_hp.clear()
    boss_hp.extend([100, 100, 100, 100, 100])


# 查詢進度
def check_boss_health():
    report = ""
    for boss_number in range(1, 6):
        if boss_hp[boss_number - 1] > 0:
            report += f"第 {current_round} 階 {boss_number} 王，剩餘血量：{boss_hp[boss_number - 1]}\n"
            break
    return report


# ======================================================================================================================
#  discord general func
# ======================================================================================================================

# print message
async def send_msg(src, title='', description='', colour=discord.Colour.red(), ephemeral=True):
    embed = discord.Embed(colour=colour, title=title, description=description)
    if type(src) == discord.Interaction:
        await src.response.send_message(embed=embed, ephemeral=ephemeral)
    else:  # type(src) == discord.ext.commands.context.Context:
        await src.send(embed=embed, ephemeral=ephemeral)


# ======================================================================================================================
#  指令部分
# ======================================================================================================================

# 後端檢查
@client.event
async def on_ready():
    print('機器人已上線')


# 選單指令
@client.command()
async def menu(ctx):
    embed = discord.Embed(
        colour=discord.Colour.red(),
        title="盟戰出刀管理"
    )
    await ctx.send(embed=embed, view=SelectView(), ephemeral=True)


# 報刀指令
@client.command()
async def sign(ctx):
    await ctx.send("請選擇要刀的王", view=SelectBossView(), ephemeral=True)


# 出刀指令
@client.command()
async def attack(ctx, boss_number: int, damage: int):
    if boss_number < 1 or boss_number > 5:
        await send_msg(ctx, title="請輸入有效的王 (1-5)")
        return

    boss_index = boss_number - 1
    boss_hp[boss_index] -= damage

    if boss_hp[boss_index] <= 0:
        await send_msg(ctx, title=f"{boss_number}王已被消滅！", ephemeral=False)
        boss_hp[boss_index] = 0
        clear_single_boss_report(boss_number)

        if boss_number == 5:
            if current_round == 10:
                await send_msg(ctx, title="本次盟戰已結束", ephemeral=False)
            else:
                await send_msg(ctx, title="五王已被消滅，已清空刀表並進入下一階段", ephemeral=False)
            clear_boss_reports()
            next_round()
            return

    member = ctx.author
    add_boss_report(current_round, boss_number, "刪除", member)
    if boss_hp[boss_index] >= 0:
        await send_msg(ctx, title=f"{boss_number}王，剩餘血量：{boss_hp[boss_index]}", ephemeral=False)


# 列出刀表指令
@client.command()
async def list(ctx):
    await send_msg(ctx, title=generate_report())


# 進度指令
@client.command()
async def now(ctx):
    health_report = check_boss_health()
    if health_report:
        await send_msg(ctx, title=check_boss_health())
    else:
        await send_msg(ctx, title="所有王都已被消滅！")


# "指令"指令
@client.command()
async def command(ctx):
    await send_msg(ctx, title="指令列表", description="\n".join(Data.cmd_list))


# 血量指令
@client.command()
async def health(ctx, hp_string: str):
    hp_values = hp_string.split(',')

    if len(hp_values) != 5:
        await send_msg(ctx, title="請提供五個王的血量 (用逗號分隔)")
        return

    try:
        boss_hp.clear()
        boss_hp.extend([int(hp) for hp in hp_values])

        await send_msg(ctx, title="王的血量已設定成功")
    except ValueError:
        await send_msg(ctx, title="請確保血量為有效的數字")


# 清空指令
@client.command()
async def clear(ctx):
    clear_boss_reports()
    await send_msg(ctx, title="已清空刀表", ephemeral=False)


# 階段指令
@client.command()
async def phase(ctx, round_number: int):
    global current_round
    if round_number < 1 or round_number > 10:
        await send_msg(ctx, title="請輸入有效的階段數 (1-10)")
        return

    current_round = round_number
    clear_boss_reports()
    await send_msg(ctx, title=f"已設定階段為 {round_number}，並清空刀表", ephemeral=False)


# 重設指令
@client.command()
async def reset(ctx):
    global current_round
    clear_boss_reports()
    current_round = 1

    await send_msg(ctx, title="已重設刀表", ephemeral=False)


# For fun
@client.command()
async def 代刀(ctx):
    await send_msg(ctx, title="@Woody#9309 無敵爸爸 救救我", ephemeral=False)


# ======================================================================================================================
#  main
# ======================================================================================================================

token = ''
client.run(token)