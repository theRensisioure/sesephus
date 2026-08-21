---
title: "Sisyphus, Flipped"
subtitle: "Circadian Entrainment, Audio Journaling, and AI as a Cognitive Prosthetic"
date: "2026-06-14"
tags:
  - circadian
  - recovery
  - audio-journaling
  - alarm-engine
  - cognitive-prosthetic
  - zig
  - local-ai
excerpt: "I left my first rehab two weeks early. The official excuse was a bad roommate situation. The real reason was $8,000 for egregiously suboptimal therapeutic care. In places that confiscate your phone, the least they can do is give you a real replacement — not for scrolling, but for remembering what time actually feels like."
---

# Sisyphus, Flipped

The second time I pulled up to the first rehab I went to, I left two weeks early.

I gave them a **** excuse. The real reason was that I was paying $8,000 for suboptimal — *egregiously* suboptimal — therapeutic services, and I didn't know how to tell them that without getting into a whole ego debate with the facility. So I said the roommate and I had deep history and beef, and I wasn't sure he wasn't going to go postal. That part wasn't entirely a lie. I was genuinely uncertain.

But if the facility had at least provided *supplementative* therapeutic care, I think I would have stayed the whole way through.

I don't think even that would have magically fixed my specific case. What I *do* think is that in rehabs where they typically take your phone, it is most necessary to provide a replacement. And that replacement is **not** for texting other people. It's not for entertainment.

It's for **circadian entrainment**.

## What Circadian Entrainment Actually Means Here

Circadian entrainment is the process of reminding the brain how long time actually occurs within — how fast time moves, what a real hour feels like when you're cut off from normal cues.

When your phone is taken, you lose one of the most powerful external clocks most people have. Without it, days blur. Therapy that is already suboptimal becomes even less effective because the basic rhythm of the day is broken.

A shallow fix would be a basic alarm engine. We can do much better.

With user permission, through a defined microphone source, the system can capture audio clips in three varying sizes:

- **30 seconds**
- **60 seconds** 
- **90 seconds**

These are not voice memos for later entertainment. They are structured, intentional audio journal entries — short enough to be sustainable, long enough to capture real reflection.

## The Hardware Trap (And How to Avoid It)

The tricky part is bypassing the need for a custom manufactured device.

Most "solutions" don't account for the fact that the human body moves. You're going to be far from the microphone at some point. I contemplated a necklace, a wristband, or some little companion device that pairs with the phone so you could raise it to your face and speak into it.

But that would make the entire problem space ten times harder. Now you have to design PCBs, understand manufacturing tolerances, deal with ordering runs, and pray you didn't get anything a hair wrong on the first revision. That path turns a simple app into a hardware company.

The beauty of circadian entrainment is that you don't need the necklace.

You can use the phone you already have (or the replacement device the facility provides) and build the entire interface in software.

## Sesefus (Sisyphus, Spelt Differently)

This is the core idea behind **Sesefus** (the CLI command is `ssfs`).

Sisyphus is about flipping the folk tale on its head. Instead of being punished by endlessly pushing a boulder up a hill (or, in the modern version, burning out from your own intellect), you utilize AI as a **cognitive prosthetic**. The goal is to better your own mind in a way that doesn't require money, healthcare insurance, or a professional — though it would benefit greatly from a professional's *assistant* (i.e., designed to be supplementative therapy).

Because of the irony, we spell it differently: **Sesefus**.

The backbone is the command-line interface. All actions the app can take for the user are referenced by the brief `ssfs` prefix, followed by category, command, variable flags, and other variables.

## Rich Alarm Interface on a Shared Architecture

The alarm system is not just "set a reminder."

You'd be able to:
- Group alarms by day
- Further group them by category of intent
- Save and swap entire **profiles for the week**

Example: You want all your Mondays at 9am to trigger a particular thing. Save that configuration as a profile. Later you can swap the entire 9am slot between different profiles without editing one by one by one.

Future machine learning features include using embedding spaces to match verses of religious texts to times of the day, localized to specific journal prompts. If a journal prompt scores highly in the embedding space with a verse from the Bible (or the Quran, or whichever text you affiliate with), the system can surface a curated notion at the next alarm that has strong resonance with what you're working on.

## Audio as First-Class Data

The three clip lengths (30/60/90s) feed into an audio database. From each entry, a 1-to-1 **artifact database** is derived (transcriptions, embeddings, metadata). This processing happens offline on the host, not in real time.

The architecture is deliberately a host + embedded client model. You can run the full host+client bundle on one machine, or copy the client executable across devices on your local network for a heterogeneous compute stack. The client handles local audio capture (Win32 waveIn or equivalent). The host manages schedules, vault storage, and coordinates.

This is already partially implemented in Zig as the Circadia / Sesephus alarm engine (host daemon + edge clients communicating over length-prefixed TCP frames, with HTTP control surface and audio journaling paths).

## Local AI, Not Cloud Dependency

Sesefus is designed to scale to localized, hardware-accelerated machine learning inference on the audio and artifact databases.

The vLLM porting work happening in parallel (Crow-9B-HERETIC via local OpenAI-compatible endpoint) is part of the same prosthetic layer — bringing high-quality language model assistance (for prompt matching, journal reflection suggestions, etc.) without sending your private reflections anywhere.

## Why This Matters

In recovery environments (and honestly, in ordinary life under stress), the difference between "I have a phone taken away" and "I have a structured, private, time-aware prosthetic that helps me remember what a day actually is" is enormous.

It turns the confiscated phone from a punishment into an opportunity for a better-designed replacement.

No custom hardware. No $8,000 for half-baked therapy. Just reliable software, audio that respects the user's real state, rich scheduling that actually matches how humans live their weeks, and local AI that acts as an assistant rather than a replacement for a real person.

Sisyphus doesn't have to push the boulder alone anymore.

---

**Related artifacts in the repo:**

- `core/sesephus/` — Zig Circadia alarm engine (**not done**; `alarm *` wired; `journal` / `rhythm` stubs)
- `ssfs.bat` — launcher for `sesefus.exe`
- `apps/journal-daemon/` — Python dogfood stand-in (Sound Recorder + alarm poll), not the Zig daemon
- LeadLogic-Engine vLLM work (Crow-9B local inference path) for the embedding + reflection layer

The system is already moving from concept toward a working offline-first, audio-first, network-aware prosthetic. The personal experience of leaving that rehab early is part of why the circadian + supplementative audio layer is non-negotiable.

*This is a research / personal systems note for the profile site.*

Sissyphus, in Renaissance or REnisioure le sesefu, the ancient folk lore, the pervasion notion of a conceptual nacho or what quin and i like to say when 'your reheating someones nachos', which is arriving at the same conclusion as acedmeic rigor and basically on raw talent, and sheeer odds alone. No, its just whe nyou are doing something someone seens someone else do, and they wanna talk about it and other things... may lord have mercy on that soul..
