import { rememberPen, type PenSettings, type Rgba } from '@study-lens/core';
import type { ReactElement } from 'react';

interface PenSettingsDialogProps {
  pen: PenSettings;
  recent: PenSettings[];
  onChange: (pen: PenSettings) => void;
  onRecent: (recent: PenSettings[]) => void;
  onClose: () => void;
}

export function PenSettingsDialog(props: PenSettingsDialogProps): ReactElement {
  const { pen } = props;
  const setChannel = (channel: keyof Rgba, value: number): void => {
    props.onChange({ ...pen, color: { ...pen.color, [channel]: value } });
  };

  return (
    <section className="pen-dialog" role="dialog" aria-label="Pen Settings">
      <h2>Pen Settings</h2>
      <label>
        Red
        <input
          type="range"
          min={0}
          max={255}
          value={pen.color.r}
          style={{ accentColor: '#c23b3b' }}
          onChange={(event) => setChannel('r', Number(event.target.value))}
        />
      </label>
      <label>
        Green
        <input
          type="range"
          min={0}
          max={255}
          value={pen.color.g}
          style={{ accentColor: '#2f8f4e' }}
          onChange={(event) => setChannel('g', Number(event.target.value))}
        />
      </label>
      <label>
        Blue
        <input
          type="range"
          min={0}
          max={255}
          value={pen.color.b}
          style={{ accentColor: '#2d6cdf' }}
          onChange={(event) => setChannel('b', Number(event.target.value))}
        />
      </label>
      <label>
        Opacity
        <input
          type="range"
          min={0}
          max={255}
          value={pen.color.a}
          onChange={(event) => setChannel('a', Number(event.target.value))}
        />
      </label>
      <label>
        Size
        <input
          type="range"
          min={1}
          max={40}
          value={pen.width}
          onChange={(event) => props.onChange({ ...pen, width: Number(event.target.value) })}
        />
      </label>
      <p className="field-label">Preview</p>
      <div className="pen-preview" aria-hidden="true">
        <span style={{ background: rgba(pen.color) }} />
        <i
          style={{
            background: rgba(pen.color),
            width: pen.width,
            height: pen.width,
          }}
        />
        <span style={{ background: rgba(pen.color) }} />
      </div>
      <p className="field-label">Recent Pens</p>
      <div className="recent-pens">
        {Array.from({ length: 6 }, (_, index) => {
          const recent = props.recent[index];
          return (
            <button
              key={index}
              type="button"
              disabled={!recent}
              aria-label={recent ? `Recent pen ${index + 1}` : `Empty recent pen ${index + 1}`}
              onClick={() => {
                if (recent) props.onChange(recent);
              }}
            >
              {recent ? <i style={{ background: rgba(recent.color), width: Math.min(24, recent.width), height: Math.min(24, recent.width) }} /> : null}
            </button>
          );
        })}
      </div>
      <button
        type="button"
        className="primary"
        onClick={() => {
          props.onRecent(rememberPen(props.recent, pen));
          props.onClose();
        }}
      >
        Save and Close
      </button>
    </section>
  );
}

function rgba(color: Rgba): string {
  return `rgba(${color.r}, ${color.g}, ${color.b}, ${color.a / 255})`;
}
