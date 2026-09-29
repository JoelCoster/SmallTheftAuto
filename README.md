# Small Theft Auto

![Small Theft Auto on the Arduboy FX](media/clip.gif)

An open-world crime game in 3D for the **Arduboy FX**: a city on two islands,
with cars to take, police, and so far twelve missions.

I recorded some gameplay on my Arduboy FX: [video on YouTube](https://www.youtube.com/watch?v=kIbBKJJ0JOA)

## Play

Download [SmallTheftAuto.arduboy](download/SmallTheftAuto.arduboy).

- Made for the original Arduboy FX. Not tried on the FX-C or the Mini.
- In the browser: drop the file on the
  [Ardens player](https://tiberiusbrown.github.io/Ardens/player.html).

## Controls

| | On foot | In a car |
|---|---|---|
| Up | Run | |
| Left, Right | Turn | Steer |
| B (upper) | Fire | Accelerate |
| A (lower) | With Up: sprint | Brake, reverse |
| Down | Answer the telephone, get in | Get out |

Left + Right opens the map.

## Build

```bash
tools/build.sh
```

What it needs: [docs/build.md](docs/build.md).
Everything else: [docs/notes.md](docs/notes.md).
