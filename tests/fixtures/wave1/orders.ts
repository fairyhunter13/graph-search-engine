import type { Money } from "./money";
import { TAXES, convert } from "./rates";
import * as log from "./log";

export class Order {
  lines: Money[] = [];

  subtotal(): Money {
    return this.lines[0];
  }

  tax(): Money {
    return convert(this.subtotal());
  }
}

export function load(root: string): Order {
  log.info(root);
  return new Order();
}
