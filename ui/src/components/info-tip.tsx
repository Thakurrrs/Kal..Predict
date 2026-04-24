import React from "react";

type InfoTipProps = {
  text: string;
};

export function InfoTip({ text }: InfoTipProps) {
  return (
    <span className="info-tip" tabIndex={0} aria-label={text}>
      i
      <span className="info-tip-popover">{text}</span>
    </span>
  );
}
