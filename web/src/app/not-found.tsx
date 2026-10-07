import { ButtonLink } from "@/components/ui";

export default function NotFound() {
  return (
    <section className="container-x py-32 text-center">
      <div className="eyebrow">404</div>
      <h1 className="mt-3 text-[40px] font-semibold tracking-tight">Nothing planted here.</h1>
      <div className="mt-8">
        <ButtonLink href="/">Back to the farm</ButtonLink>
      </div>
    </section>
  );
}
