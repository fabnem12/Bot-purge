import asyncio
import discord
import pickle
import os
from discord.ext import commands
from datetime import datetime, timedelta
from random import randint

from constantes import TOKEN #le token du bot pour se connecter à discord

if os.path.exists("derniereActivite.p"):
    derniereActivite = pickle.load(open("derniereActivite.p", "rb").)
else:
    derniereActivite = dict()
    #dictionnaire qui à chaque membre du serveur associe sa date de dernière activité

def save():
    pickle.dump(derniereActivite, open("derniereActivite.p", "wb"))

def ajoutActivite(idMembre, datetime, sauvegardeEnvisageable = True):
    if idMembre not in derniereActivite or datetime > derniereActivite[idMembre]:
        derniereActivite[idMembre] = datetime

    if sauvegardeEnvisageable and randint(0, 10) < 1: save()

def maintenant():
    return datetime.utcnow()

def main():
    bot = commands.Bot(command_prefix="P.", help_command = None)

    @bot.event
    async def on_raw_reaction_add(payload):
        ajoutActivite(payload.user_id, maintenant())

    @bot.event
    async def on_message(msg):
        ajoutActivite(msg.author.id, msg.created_at)
        await bot.process_commands(msg)

    @bot.command(name = "reset")
    async def reset(ctx):
        if ctx.author.id != ctx.guild.owner_id or not ctx.author.guild_permissions.administrator: return
        await ctx.message.add_reaction("🕰️")

        derniereActivite.clear()
        save()

        for salon in ctx.guild.text_channels:
            try:
                async for message in salon.history(limit = None):
                    await ajoutActivite(message.author.id, message.created_at, False)
            except Exception as e: #le bot n'a pas le droit de lire ce salon, on passe au suivant
                pass

        save()
        await ctx.message.add_reaction("👌")

    @bot.command(name = "moins_actifs")
    async def moinsActifs(ctx):
        if ctx.author.id != ctx.guild.owner_id or not ctx.author.guild_permissions.administrator: return

        triParDateActivite = sorted(derniereActivite.items(), key=lambda x: x[1])
        laMaintenant = maintenant()

        txt = ""
        for idMembre, dateActivite in triParDateActivite:
            if laMaintenant - dateActivite < timedelta(days = 30):
                break #on a atteint 1 membre qui a été actif il y a moins de 30 jours
                #les suivants ont été actifs plus récément encore, donc on arrête
            else: #plus d'un mois depuis la dernière activité : danger
                try:
                    membre = await ctx.guild.fetch_member(idMembre)
                except: #le membre n'existe pas : a quitté le serveur
                    del derniereActivite[idMembre]
                    save()
                else:
                    txt += f"{membre.nick or membre.name} - dernière activité : {dateActivite}\n"

        with open("rapportInactifs.txt", "w") as f:
            f.write(txt)

        await ctx.channel.send(file = discord.File("rapportInactifs.txt"))

    @bot.command(name = "purgeKick")
    async def purgeKick(ctx):
        if ctx.author.id != ctx.guild.owner_id: return
        laMaintenant = maintenant()

        for idMembre, dateActivite in list(derniereActivite.items()):
            if laMaintenant - dateActivite > timedelta(days = 90): #dernière activité il y a plus de 3 mois, on purge !
                try:
                    membre = await ctx.guild.fetch_member(idMembre)
                except: #le membre n'existe pas : a quitté le serveur
                    del derniereActivite[idMembre]
                    save()
                else:
                    await membre.kick(reason = "Aucune activité sur le serveur depuis plus de 3 mois")

    @bot.command(name = "purgeRole")
    async def purgeRetraitRole(ctx, roleARetirerPurge):
        if ctx.author.id != ctx.guild.owner_id: return
        laMaintenant = maintenant()

        role = ctx.get_role(roleARetirerPurge)

        for idMembre, dateActivite in list(derniereActivite.items()):
            if laMaintenant - dateActivite > timedelta(days = 90): #dernière activité il y a plus de 3 mois, on purge !
                try:
                    membre = await ctx.guild.fetch_member(idMembre)
                except: #le membre n'existe pas : a quitté le serveur
                    del derniereActivite[idMembre]
                    save()
                else:
                    await membre.remove_roles(role)

    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(TOKEN))
    loop.run_forever()

main()
