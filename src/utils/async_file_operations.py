"""Async file I/O operations using aiofiles."""

import aiofiles
import asyncio
from pathlib import Path
from typing import Optional
from filelock import FileLock


async def async_read_file(
    path: Path | str,
    encoding: str = 'utf-8',
    timeout: Optional[float] = 10.0
) -> str:
    """
    Read a file asynchronously with locking.
    
    Args:
        path: Path to the file
        encoding: File encoding
        timeout: Lock timeout in seconds
        
    Returns:
        File contents
        
    Raises:
        FileNotFoundError: If file doesn't exist
        TimeoutError: If lock cannot be acquired
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    # Use file locking for concurrent safety
    lock_path = f"{path}.lock"
    lock = FileLock(lock_path, timeout=timeout)
    
    try:
        with lock.acquire(timeout=timeout):
            async with aiofiles.open(path, mode='r', encoding=encoding) as f:
                content = await f.read()
                return content
    except Exception as e:
        if "Timeout" in str(e):
            raise TimeoutError(f"Could not acquire lock for {path} within {timeout} seconds")
        raise


async def async_write_file(
    path: Path | str,
    content: str,
    encoding: str = 'utf-8',
    timeout: Optional[float] = 10.0,
    create_parents: bool = True
) -> None:
    """
    Write to a file asynchronously with locking.
    
    Args:
        path: Path to the file
        content: Content to write
        encoding: File encoding
        timeout: Lock timeout in seconds
        create_parents: Create parent directories if they don't exist
        
    Raises:
        TimeoutError: If lock cannot be acquired
    """
    path = Path(path)
    
    # Create parent directories if needed
    if create_parents:
        path.parent.mkdir(parents=True, exist_ok=True)
    
    # Use file locking for concurrent safety
    lock_path = f"{path}.lock"
    lock = FileLock(lock_path, timeout=timeout)
    
    try:
        with lock.acquire(timeout=timeout):
            async with aiofiles.open(path, mode='w', encoding=encoding) as f:
                await f.write(content)
    except Exception as e:
        if "Timeout" in str(e):
            raise TimeoutError(f"Could not acquire lock for {path} within {timeout} seconds")
        raise


async def async_append_file(
    path: Path | str,
    content: str,
    encoding: str = 'utf-8',
    timeout: Optional[float] = 10.0,
    create_if_missing: bool = True
) -> None:
    """
    Append to a file asynchronously with locking.
    
    Args:
        path: Path to the file
        content: Content to append
        encoding: File encoding
        timeout: Lock timeout in seconds
        create_if_missing: Create file if it doesn't exist
        
    Raises:
        FileNotFoundError: If file doesn't exist and create_if_missing is False
        TimeoutError: If lock cannot be acquired
    """
    path = Path(path)
    
    if not path.exists() and not create_if_missing:
        raise FileNotFoundError(f"File not found: {path}")
    
    # Create parent directories if needed
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    
    # Use file locking for concurrent safety
    lock_path = f"{path}.lock"
    lock = FileLock(lock_path, timeout=timeout)
    
    try:
        with lock.acquire(timeout=timeout):
            mode = 'a' if path.exists() else 'w'
            async with aiofiles.open(path, mode=mode, encoding=encoding) as f:
                await f.write(content)
    except Exception as e:
        if "Timeout" in str(e):
            raise TimeoutError(f"Could not acquire lock for {path} within {timeout} seconds")
        raise


async def async_exists(path: Path | str) -> bool:
    """
    Check if a file exists asynchronously.
    
    Args:
        path: Path to check
        
    Returns:
        True if file exists, False otherwise
    """
    return await asyncio.to_thread(Path(path).exists)


async def async_list_dir(
    path: Path | str,
    pattern: Optional[str] = None
) -> list[Path]:
    """
    List directory contents asynchronously.
    
    Args:
        path: Directory path
        pattern: Optional glob pattern to filter files
        
    Returns:
        List of paths in the directory
        
    Raises:
        NotADirectoryError: If path is not a directory
    """
    path = Path(path)
    
    if not path.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")
    
    if pattern:
        return await asyncio.to_thread(lambda: list(path.glob(pattern)))
    else:
        return await asyncio.to_thread(lambda: list(path.iterdir()))