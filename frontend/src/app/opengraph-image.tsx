import { ImageResponse } from 'next/og';

export const runtime = 'edge';
export const alt = 'ECO-Compliance Engine — Plateforme d’audit juridique souverain CEDEAO / UEMOA / OHADA';
export const size = {
  width: 1200,
  height: 630,
};
export const contentType = 'image/png';

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          padding: '64px 72px',
          background: 'linear-gradient(135deg, #001E40 0%, #003D7A 55%, #0052A5 100%)',
          color: '#FFFFFF',
          fontFamily: 'sans-serif',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: '14px',
              background: '#FFFFFF',
              color: '#0052A5',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '26px',
              fontWeight: 800,
            }}
          >
            ECE
          </div>
          <div style={{ fontSize: '22px', fontWeight: 600, color: '#D0E3F5' }}>
            ECO-Compliance Engine
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '940px' }}>
          <div style={{ fontSize: '54px', fontWeight: 800, lineHeight: 1.15, letterSpacing: '-0.02em' }}>
            Audit documentaire automatisé et conformité juridique souveraine
          </div>
          <div style={{ fontSize: '26px', lineHeight: 1.4, color: '#D0E3F5' }}>
            Corpus officiel CEDEAO · UEMOA · OHADA · OAPI · Droits nationaux — Score stabilisé, hiérarchie des normes et piste d&apos;audit.
          </div>
        </div>

        <div style={{ display: 'flex', gap: '16px', fontSize: '18px', fontWeight: 600 }}>
          <div style={{ padding: '10px 20px', borderRadius: '999px', background: 'rgba(255,255,255,0.14)' }}>
            Article-RAG Hybride
          </div>
          <div style={{ padding: '10px 20px', borderRadius: '999px', background: 'rgba(255,255,255,0.14)' }}>
            Hiérarchie &amp; Conflits
          </div>
          <div style={{ padding: '10px 20px', borderRadius: '999px', background: 'rgba(0,123,63,0.45)', border: '1px solid #75C396' }}>
            Rapport Unifié PDF
          </div>
        </div>
      </div>
    ),
    size,
  );
}
