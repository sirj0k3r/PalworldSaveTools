# pst-performance — Performance optimization patterns for PST

Load when touching any code that iterates CharacterSaveParameterMap, ItemContainerSaveData, DynamicItemSaveData, calls `add_item()`, `save()`, or processes per-player operations in loops.

## Core anti-patterns to flag

### 1. save() called per item in a loop

`PlayerInventory.add_item()` calls `self.save()` internally, which scans **ALL ItemContainerSaveData** in `loaded_level_json` + calls `sync_dynamic_items_with_registry`. Each scan is O(N_world_containers).

**WRONG:**
```python
for item_id in missing_items:
    inv.add_item('key', item_id, 1)  # save() per iteration
```

**RIGHT:**
```python
std_container = inv.get_container('key')._standardized_container
for item_id in missing_items:
    std_container.add_item(item_id, 1)  # pure in-memory, no save
inv.save()  # one save after loop
```

`StandardizedContainer.add_item()` at `standardized_container.py:118` is pure in-memory. No save, no disk I/O.

### 2. Linear char_map scan inside per-slot loop

Iterating CharacterSaveParameterMap with `next((c for c in char_map if ...))` inside a loop over slots creates O(slots × char_map) complexity.

**WRONG:**
```python
for slot in slots:
    ch = next((c for c in char_map if c['key']['InstanceId']['value'] == slot_id), None)
```

**RIGHT:**
```python
instance_lookup = {str(e['key']['InstanceId']['value']): e for e in char_map}
for slot in slots:
    ch = instance_lookup.get(slot_id)
```

### 3. Scanning the same data source multiple times

Don't iterate `CharacterSaveParameterMap`, `GroupSaveDataMap`, or `ItemContainerSaveData` twice when one pass suffices.

**WRONG:** Two separate loops for nicknames + detection.
**RIGHT:** Merge conditions into one pass with `if/elif`.

**WRONG:** `_build_level_map()` + `_build_pal_count_map()` as separate functions.
**RIGHT:** Single `_build_maps()` returning `(level_map, pal_count_map)` tuple.

### 4. No caching for repeated JSON reads

If a function reads a JSON file from disk every call and is called often, add `@lru_cache` or a module-level cache dict.

**WRONG:** `load_game_data_map(fname, key)` reads `resources/game_data/{fname}` from disk every call.
**RIGHT:** `@lru_cache(maxsize=32)` on the function.

**WRONG:** `_load_boss_key_map()` reads `boss_mapping.json` every call.
**RIGHT:** Module-level `_BOSS_KEY_CACHE = None` with lazy init.

### 5. Rebuilding lookup dicts per player

If you iterate players and rebuild a dict from the same static data each iteration, lift the build outside.

**WRONG:**
```python
for uid in player_uids:
    container_lookup = {c['key']['ID']['value']: c for c in item_containers}
    ...
```

**RIGHT:**
```python
container_lookup = {c['key']['ID']['value']: c for c in item_containers}
for uid in player_uids:
    ...
```

### 6. Triple-nested container scans

Scanning all containers → all map objects → all modules per container. Build a reverse lookup dict first.

**WRONG:**
```python
for cont in item_containers:
    for obj in map_objects:
        for module in obj['ConcreteModel']['ModuleMap']['value']:
            ...
```

**RIGHT:**
```python
container_id_to_obj = {str(module.target_container_id): obj for obj in map_objects for module in ...}
for cont in item_containers:
    obj = container_id_to_obj.get(container_id)
```

### 7. Parallelizing independent per-player disk writes

Player .sav writes (Oodle compression) are CPU-heavy and file-independent. Use ThreadPoolExecutor with `max_workers=min(os.cpu_count() or 4, 8)`.

### 8. Non `PlayerInventory.load()` won't decode Level.sav

`PlayerInventory.load()` at `inventory_manager.py:405` only decodes the **per-player** .sav file. Level.sav data comes from `constants.loaded_level_json` (already in memory). Don't worry about Level.sav re-decodes — they don't happen in inventory operations.

## Key file locations

| File | Key functions |
|------|--------------|
| `inventory_manager.py:641` | `PlayerInventory.add_item()` — triggers `save()` |
| `inventory_manager.py:703` | `PlayerInventory.save()` — scans all world containers |
| `standardized_container.py:118` | `StandardizedContainer.add_item()` — safe for loops (no save) |
| `loading_manager.py` | `run_with_loading()` — used for async UI tasks |
| `character_transfer.py:612` | `migrate_inventory_via_player_inventory` — has the loop-save pattern |
| `character_transfer.py:1040` | `gather_and_update_dynamic_containers` — build reverse lookup dicts |
