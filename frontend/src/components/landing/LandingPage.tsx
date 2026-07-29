import { HeroSection } from './HeroSection';
import { AboutSection } from './AboutSection';
import { ToolCapabilities } from './ToolCapabilities';
import { HowItWorks } from './HowItWorks';
import { LandingFooter } from './LandingFooter';

export const LandingPage = () => {
  return (
    <div className="min-h-screen bg-black text-white">
      <HeroSection />
      <AboutSection />
      <ToolCapabilities />
      <HowItWorks />
      <LandingFooter />
    </div>
  );
};
