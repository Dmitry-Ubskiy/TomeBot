import asyncio
import discord
import json
import random
import operator
import re

#operator look up table for the diceroller
operators = {"+": operator.add, "-": operator.sub,
             "*": operator.mul, "/": operator.truediv}

#edit these values if you want to load the various json files from different folders.
paths = {"license":"license.json","spells":"spells.json","monsters":"monsters.json","token":"token.json","log":"log.json"}

license = {}
with open(paths["license"],'r') as fp:
    license = json.load(fp)

spells = {}
with open(paths["spells"],'r') as fp:
    spells = json.load(fp)

monsters = {}
with open(paths["monsters"],'r') as fp:
    monsters = json.load(fp)

tokens = {}
with open(paths["token"],'r') as fp:
    tokens = json.load(fp)

log = {}
with open(paths["log"],'r') as fp:
    log = json.load(fp)

token = tokens['token']

class TomeBot(discord.Client):
    def __init__(self):
        super().__init__()
        self.GamePlaying = discord.Game()
        self.GamePlaying.name = "Type ?commands"

    async def on_message(self, message):
        global log
        if message.content.startswith("?"):
            if len(log) > 9:
                log = log[-9:]
            try:
                messagelog = {"messageID":message.id,"userID":message.author.id,"username":message.author.name,"timestamp":str(message.timestamp),"content":message.content,"serverID":message.server.id,"servername":message.server.name,"channelID":message.channel.id,"channelname":message.channel.name,"privatemessage":False}
            except:
                messagelog = {"messageID":message.id,"userID":message.author.id,"username":message.author.name,"timestamp":str(message.timestamp),"content":message.content,"privatemessage":True}
            log.append(messagelog)
            with open(paths["log"],'w') as fp:
                json.dump(log, fp)
            command = (message.content.split(' ',1)[0])[1:]
            if hasattr(self, command):
                response = getattr(self, command)(message)
                if response[0] != None:
                    for a in response:
                        await self.send_message(message.channel, a)


    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')
        await self.change_status(self.GamePlaying, idle = False)

    def commands(self, message):
        response= """
Commands:
?roll - roll dice, syntax ?roll xdy
?spellsearch - search for a dnd 5e spell
?spellinfo - get information about a specific dnd 5e spell
?monstersearch - search for a dnd 5e monster
?monsterinfo - get information about a specific dnd 5e monster
?dminfo - like monsterinfo, but also gives stats such as armor class, hp etc.

To find this bot in its main server (which it was built for) join here:
https://discord.gg/25bf5NT

also on github too!
https://github.com/Carbsta/TomeBot
If you want to help me implement Volo's, or work on the SRD version come find me here.

Hosted by @Crablabuk.

To add to your server use this link:
https://discordapp.com/oauth2/authorize?client_id=247413966094073856&scope=bot&permissions=0
(it doesn't require any permisions and never will)
"""
        return([response])

    def tokenize_roll(self, expression):
        lexem_regex = r'\d*d\d+|\d*\.\d+|\d+|[-+*/()]'
        lexems = re.findall(lexem_regex, expression)

        # check that we don't have any extra junk
        if ''.join(re.split(lexem_regex, expression)).strip() != '':
            raise Exception

        tokens = []

        dice_regex = re.compile(r'\d*d\d+')
        int_regex = re.compile(r'\d+')
        float_regex = re.compile(r'\d*\.\d+')

        for lex in lexems:
            if lex in ("(", ")", "-", "+", "*", "/"):
                tokens.append([lex])
            elif dice_regex.match(lex):
                num, sides = lex.split('d')
                num = "1" if num == "" else num
                tokens.append(["DICE", int(num), int(sides)])
            elif int_regex.match(lex):
                tokens.append(["NUM", int(lex)])
            elif float_regex.match(lex):
                tokens.append(["NUM", float(lex)])

        return tokens

    def evaluate_roll(self, tokens):
        # evaluate dice first:
        result_str = ["Rolling: "]
        for i, t in enumerate(tokens):
            if t[0] == "DICE":
                rolls = []
                roll_total = 0
                for n in range(t[1]):
                    roll = random.randint(1, t[2])
                    rolls.append(str(roll))
                    roll_total += roll
                result_str.append("(" + "+".join(rolls) + ")")
                tokens[i] = ["NUM", roll_total]
            elif t[0] == "NUM":
                result_str.append(str(t[1]))
            else:
                result_str.append(t[0])

        # reorder as per RPN
        queue = []
        stack = []

        muldiv = ("*", "/")
        addsub = ("+", "-")
        ops = muldiv + addsub

        for t in tokens:
            if t[0] == "NUM":
                queue.append(t[1])
            elif t[0] in muldiv:
                if stack and stack[-1] in muldiv:
                    queue.append(stack[-1])
                    stack = stack[:-1]
                stack.append(t[0])
            elif t[0] in addsub:
                while stack and stack[-1] in ops:
                    queue.append(stack[-1])
                    stack = stack[:-1]
                stack.append(t[0])
            elif t[0] == "(":
                stack.append(t[0])
            elif t[0] == ")":
                if stack:
                    while stack[-1] != "(":
                        queue.append(stack[-1])
                        stack = stack[:-1]
                stack = stack[:-1]

        queue += reversed(stack)

        # evaluate
        stack = []

        for t in queue:
            if type(t) in (int, float):
                stack.append(t)
            else:
                stack[-2] = operators[t](stack[-2], stack[-1])
                stack = stack[:-1]

        if len(stack) != 1:
            raise Exception

        if type(stack[0]) == float and stack[0].is_integer():
            stack[0] = int(stack[0])

        result_str += [" = ", str(stack[0])]

        return "".join(result_str)

    def roll(self, message):
        try:
            if not message.content.startswith("?roll "):
                raise Exception
            expression = message.content[6:]
            tokens = self.tokenize_roll(expression)
            rolls = self.evaluate_roll(tokens)
        except:
            rolls = "Don't do stupid stuff with the Roll command."
        return ([rolls])

    def spellinfo(self, message):
        searchterm = message.content.split(' ',1)[1].lower()
        results = []
        result = "Could not find that spell, use ?spellsearch to get spell names."
        for x in spells:
            if searchterm == x['name'].lower():
                result = x['name']+"\n\n"+x['level']+"\n\nDescription: \n"+x['desc']
                try:
                    result = result + "\n" + x['higher_level']
                except:
                    result = result
                result = result + "\nCasting time: "+x['casting_time']+"\nDuration: "+x['duration']+"\nRange: "+x['range']
                result = result + "\n\nConcentration: "+x['concentration']+"\nRitual: "+x['ritual']+"\n\nComponents: "+x['components']
                try:
                    result = result + "\nMaterials: "+x['material']
                except:
                    result = result
                result = result + "\n\nClass: "+x['class']
        results = [result]
        if len(result)>1999:
            firstpart, secondpart = result[:len(result)//2], result[len(result)//2:]
            results = [firstpart,secondpart]

        return(results)

    def spellsearch(self, message):
        searchterms = message.content.split(' ',1)[1].lower()
        searchterms = searchterms.split(", ")
        results = "Results: \n"
        for spell in spells:
            matches = 0
            for term in searchterms:
                if term in spell['name'].lower():
                    matches = matches + 1
                elif term in spell['class'].lower():
                    matches = matches + 1
                elif term in spell['school'].lower():
                    matches = matches + 1
                elif term in spell['duration'].lower():
                    matches = matches + 1
                elif term in spell['range'].lower():
                    matches = matches + 1
                elif ", M" in spell["components"]:
                    if term in spell["material"]:
                        matches = matches + 1
            if matches == len(searchterms):
                results = results+spell['name']+"\n"
        if len(results)>1990:
            results = "Too many results found, try narrowing your search with more search terms."
        return([results])

    def monstersearch(self,message):
        searchterm = message.content.split(' ',1)[1].lower()
        searchterm = searchterm.split(", ")
        results = "Results: \n"
        for monster in monsters:
            matches = 0
            for term in searchterm:
                if term in monster['name'].lower():
                    matches = matches + 1
                elif term in monster['size'].lower():
                    matches = matches + 1
                elif term in monster['type'].lower():
                    matches = matches + 1
                elif term in monster['subtype'].lower():
                    matches = matches + 1
                elif term in monster['alignment'].lower():
                    matches = matches + 1
                elif term in monster['senses'].lower():
                    matches = matches + 1
                elif term in monster['languages'].lower():
                    matches = matches + 1
            if matches == len(searchterm):
                results = results+monster['name']+"\n"
        if len(results)>1990:
            results = "Too many results found, try narrowing your search with more search terms."
        return([results])
        
    def monsterinfo(self,message):
        searchterm = message.content.split(' ',1)[1].lower()
        result = "Could not find that monster, use ?monstersearch to get monster names."
        abilities = "No special abilities"
        actions = "No actions"
        legendaryactions = "No legendary actions"
        for x in monsters:
            if searchterm == x['name'].lower():
                result = "**"+x['name']+"**\n\n"+"Size: "+x['size']+"\nChallenge Rating: "+x['challenge_rating']+"\nType: "+x['type']
                if x['subtype'] != "":
                    result = result + "\nSubtype: "+x['subtype']
                result = result +"\nAlignment: "+x['alignment']+"\nSenses: "+x['senses']+"\nLanguages: "+x['languages']
                try:
                    abilities = "**Special abilities:**\n\n"
                    for y in x['special_abilities']:
                        abilities = abilities + y['name']+"\n"+y['desc']+"\n\n"
                except:
                    abilities = "No special abilities"
                try:
                    actions = "**Actions:**\n\n"
                    for z in x['actions']:
                        actions = actions + z['name']+"\n"+z['desc']+"\n\n"
                except:
                    actions = "No actions"
                try:
                    legendaryactions = "**Legendary Actions:**\n\n"
                    for w in x['legendary_actions']:
                        legendaryactions = legendaryactions + w['name']+"\n"+w['desc']+"\n\n"
                except:
                    legendaryactions = "No legendary actions"
                result = result + "\n\n**For DM specific info such as Stats, armor class etc, use ?dminfo instead**"
        results = [result,abilities,actions,legendaryactions]
        for b in results:
            if len(b)>1900:
                firstpart, secondpart = b[:len(b)//2], b[len(b)//2:]
                index = results.index(b)
                results.remove(b)
                results.insert(index,secondpart)
                results.insert(index,firstpart)

        return(results)

    def dminfo(self,message):
        searchterm = message.content.split(' ',1)[1].lower()
        result = "Could not find that monster, use ?monstersearch to get monster names."
        stats = "No stats"
        abilities = "No special abilities"
        actions = "No actions"
        legendaryactions = "No legendary actions"
        for x in monsters:
            if searchterm == x['name'].lower():
                result = "**"+x['name']+"**\n\n"+"Size: "+x['size']+"\nChallenge Rating: "+x['challenge_rating']+"\nType: "+x['type']
                if x['subtype'] != "":
                    result = result + "\nSubtype: "+x['subtype']
                result = result +"\nAlignment: "+x['alignment']+"\nSenses: "+x['senses']+"\nLanguages: "+x['languages']
                try:
                    abilities = "**Special abilities:**\n\n"
                    for y in x['special_abilities']:
                        abilities = abilities + y['name']+"\n"+y['desc']+"\nAttack bonus: "+str(y['attack_bonus'])+"\n\n"
                except:
                    abilities = "No special abilities"
                try:
                    actions = "**Actions:**\n\n"
                    for z in x['actions']:
                        actions = actions + z['name']+"\n"+z['desc']+"\nAttack bonus: "+str(z['attack_bonus'])
                        try:
                            actions = actions + "\nDamage dice: "+z['damage_dice']
                        except:
                            actions = actions
                        try:
                            actions = actions + "\nDamage bonus: "+z['damage_bonus']+"\n\n"
                        except:
                            actions = actions
                        actions = actions + "\n\n"
                except:
                    actions = "No actions"
                try:
                    legendaryactions = "**Legendary Actions:**\n\n"
                    for w in x['legendary_actions']:
                        legendaryactions = legendaryactions + w['name']+"\n"+w['desc']+"\nAttack bonus: "+str(w['attack_bonus'])
                        try:
                            legendaryactions = legendaryactions + "\nDamage dice: "+w['damage_dice']
                        except:
                            legendaryactions = legendaryactions
                        try:
                            legendaryactions = legendaryactions + "\nDamage bonus: "+w['damage_bonus']+"\n\n"
                        except:
                            legendaryactions = legendaryactions
                        legendaryactions = legendaryactions + "\n\n"
                except:
                    legendaryactions = "No legendary actions"

                stats = "**Stats:**\n\n"+"Armor class: "+str(x['armor_class'])+"\nHit points: "+str(x['hit_points'])+"\nHit dice: "+x['hit_dice']
                stats = stats+"\n\nSpeed: "+x['speed']+"\n\nStrength: "+str(x['strength'])+"\nDexterity: "+str(x['dexterity'])
                stats = stats+"\nConstitution: "+str(x['constitution'])+"\nIntelligence: "+str(x['intelligence'])+"\nWisdom: "+str(x['wisdom'])
                stats = stats+"\nCharisma: "+str(x['charisma'])+"\n\n"

                #getting all the random shit crazy stats that are different for each monster -.-"
                skills = ["Acrobatics","Arcana","Athletics","Deception","History","Insight","Intimidation","Investigation","Medicine","Nature","Perception","Performance","Persuasion","Religion","Stealth","Survival"]
                savingthrows = ["Strength_save","Dexterity_save","Constitution_save","Intelligence_save","Wisdom_save","Charisma_save"]
                resistances = ["Damage_vulnerabilities","Damage_resistances","Damage_immunities","Condition_immunities"]

                for skill in skills:
                    stat = x.get(skill.lower())
                    if stat != None:
                        stats = stats + skill +": "+str(stat)+"\n"
                stats = stats+"\n"

                for save in savingthrows:
                    stat = x.get(save.lower())
                    if stat != None:
                        stats = stats + save +": "+str(stat)+"\n"
                stats = stats+"\n"

                for resistance in resistances:
                    stat = x.get(resistance.lower())
                    if stat != "":
                        stats = stats + resistance +": "+stat+"\n"

        results = [result,stats,abilities,actions,legendaryactions]
        for b in results:
            if len(b)>1900:
                firstpart, secondpart = b[:len(b)//2], b[len(b)//2:]
                index = results.index(b)
                results.remove(b)
                results.insert(index,secondpart)
                results.insert(index,firstpart)
        return(results)

bot = TomeBot()
bot.run(token)