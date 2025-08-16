# Plan to Fix All 467 Basedpyright Warnings

## Warning Categories (Top Issues)

1. **Type `Any` is not allowed** - 49 instances
2. **Argument type is Any** - 37 instances  
3. **Unused call results** - 35 instances (int)
4. **Deprecated Optional syntax** - 28 instances
5. **Deprecated Dict/List imports** - 26 instances
6. **Unknown append type** - 19 instances
7. **Unknown argument types** - 17 instances

## Fix Strategy (In Order)

### Phase 1: Fix All Deprecated Syntax

- Replace `Optional[T]` with `T | None`
- Replace `Dict` with `dict`
- Replace `List` with `list`
- Replace `Tuple` with `tuple`

### Phase 2: Fix Unused Call Results

- Add `_ =` for intentionally unused results
- Most are file.write() calls

### Phase 3: Fix Missing Type Annotations

- Add type annotations to class attributes
- Add return types where missing
- Fix function parameter types

### Phase 4: Reduce Any Usage

- Replace Any with specific types where possible
- Use Union types for flexibility
- Create specific TypedDicts for dictionaries

### Phase 5: Fix Unknown Types

- Add proper type hints for append operations
- Fix unknown member types

## Files to Fix (by warning count)

1. src/utils/base_logger.py - 66 warnings
2. src/core/message_processor.py - 54 warnings
3. src/utils/archive_manager.py - 53 warnings
4. src/cli.py - 44 warnings
5. src/utils/retry.py - 42 warnings

## Safety Measures

- Run tests after each file
- Commit after each successful phase
- Use type: ignore sparingly and document why
