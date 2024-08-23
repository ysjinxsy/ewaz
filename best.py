import aiosqlite
import asyncio

async def reset_ticket_count():
    async with aiosqlite.connect('ticket.db') as conn:
        cursor = await conn.cursor()

        # Delete all records from the tickets table
        await cursor.execute('DELETE FROM tickets')

        # Optionally, reset the auto-increment counter
        await cursor.execute('DELETE FROM sqlite_sequence WHERE name="tickets"')

        await conn.commit()

    print("Ticket count has been reset to 0.")

# Run the reset function
asyncio.run(reset_ticket_count())
