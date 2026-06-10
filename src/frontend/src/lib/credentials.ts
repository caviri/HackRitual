/**
 * The credential message — what the keeper sends, by hand, to each
 * approved participant. Composed client-side so the admin's own mail
 * client (mailto:) or clipboard does the delivery; the platform itself
 * never sends email.
 */

export interface CredentialMessageInput {
  name: string;
  password: string;
  eventTitle: string;
}

export function credentialSubject(eventTitle: string): string {
  return `Your access key for ${eventTitle}`;
}

export function credentialBody({ name, password, eventTitle }: CredentialMessageInput): string {
  const origin = typeof window !== 'undefined' ? window.location.origin : '';
  return [
    `Hi ${name},`,
    '',
    `You're in — your application to ${eventTitle} has been approved.`,
    '',
    `Your personal access key is:`,
    '',
    `    ${password}`,
    '',
    `Sign in with it here: ${origin}/signin/`,
    '',
    `The key is yours alone — it identifies you, so don't share it.`,
    `If you lose it, ask an organizer for a new one.`,
    '',
    `See you in the circle.`,
  ].join('\n');
}

export function credentialMailto(email: string, input: CredentialMessageInput): string {
  const subject = encodeURIComponent(credentialSubject(input.eventTitle));
  const body = encodeURIComponent(credentialBody(input));
  return `mailto:${encodeURIComponent(email)}?subject=${subject}&body=${body}`;
}
