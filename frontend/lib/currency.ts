/** Белорусский рубль (BYN) */
export const CURRENCY_SYMBOL = "Br";

export function formatMoney(amount: number): string {
  return `${amount.toLocaleString("ru-BY")} ${CURRENCY_SYMBOL}`;
}
