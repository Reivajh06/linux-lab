import { describe, expect, it } from 'vitest';
import { plainText } from './text';

describe('plainText', () => {
  it('removes emphasis, code and links', () => {
    expect(plainText('Usa **ficheros de unidad reales** y `ps` con `-e`. Ver [man](https://x).'))
      .toBe('Usa ficheros de unidad reales y ps con -e. Ver man.');
    expect(plainText('Lee *con cuidado* y _despacio_.')).toBe('Lee con cuidado y despacio.');
  });

  it('drops block markers and collapses whitespace', () => {
    expect(plainText('# Título\n\n- uno\n- dos\n1. tres\n> cita')).toBe('Título uno dos tres cita');
  });

  it('keeps underscores and asterisks inside identifiers and globs', () => {
    expect(plainText('Edit `my_file_name` and match *.txt files')).toBe('Edit my_file_name and match *.txt files');
    expect(plainText('use snake_case_names here')).toBe('use snake_case_names here');
  });
});
