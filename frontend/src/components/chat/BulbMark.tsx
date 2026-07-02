import { IconAiBulb } from "./ChatIcons";

interface Props {
  pulse?: boolean;
}

/** AI bulb mark beside assistant messages and status rows */
export default function BulbMark({ pulse = false }: Props) {
  return (
    <span
      className={`bulb-mark${pulse ? " bulb-mark--pulse" : ""}`}
      aria-hidden="true"
    >
      <IconAiBulb />
    </span>
  );
}
