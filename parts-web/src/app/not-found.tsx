import { ButtonLink } from "@/components/ui";

export default function NotFound() {
  return (
    <section className="py-28">
      <div className="container-x">
        <div className="eyebrow">404</div>
        <h1 className="mt-3 text-[40px] font-semibold tracking-[-0.02em]">That part isn&apos;t in the catalogue.</h1>
        <ButtonLink href="/" className="mt-8">Back home</ButtonLink>
      </div>
    </section>
  );
}
