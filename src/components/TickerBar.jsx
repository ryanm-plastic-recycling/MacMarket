import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';

export default function TickerBar() {
  const [tickers, setTickers] = useState([]);

  useEffect(() => {
    fetch('/api/tickers')
      .then(r => r.json())
      .then(setTickers)
      .catch(() => setTickers([]));
  }, []);

  const onDragEnd = async (result) => {
    if (!result.destination) return;
    const reordered = Array.from(tickers);
    const [moved] = reordered.splice(result.source.index, 1);
    reordered.splice(result.destination.index, 0, moved);
    setTickers(reordered);
    await fetch('/api/tickers/order', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(reordered.map(t => t.id)),
    }).catch(() => {});
  };

  return (
    <DragDropContext onDragEnd={onDragEnd}>
      <Droppable droppableId="tickerBar" direction="horizontal">
        {(provided) => (
          <div className="ticker-bar" ref={provided.innerRef} {...provided.droppableProps}>
            {tickers.map((t, idx) => (
              <Draggable key={t.id} draggableId={String(t.id)} index={idx}>
                {(prov) => (
                  <NavLink
                    to={`/ticker/${t.symbol}`}
                    className="ticker-item"
                    ref={prov.innerRef}
                    {...prov.draggableProps}
                    {...prov.dragHandleProps}
                  >
                    {t.symbol}
                  </NavLink>
                )}
              </Draggable>
            ))}
            {provided.placeholder}
          </div>
        )}
      </Droppable>
    </DragDropContext>
  );
}
