import { Badge } from './UI';

export function statusTone(status: string): string {
  const s = status.toLowerCase();
  if (s.includes('paid') || s.includes('live') || s.includes('completed') || s.includes('active')) return 'green';
  if (s.includes('overdue') || s.includes('lost') || s.includes('rejected')) return 'red';
  if (s.includes('negotiation') || s.includes('due soon') || s.includes('pending')) return 'amber';
  if (s.includes('sent') || s.includes('upcoming') || s.includes('new') || s.includes('converted') || s.includes('issued')) return 'blue';
  return 'slate';
}

export default function Status({ value }: { value: string }) {
  return <Badge tone={statusTone(value)}>{value}</Badge>;
}
