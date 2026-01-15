import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  KeyRound,
  Code,
  BarChart3,
  AlertTriangle,
  BookOpen,
  Check,
  Copy,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface HelpDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const steps = [
  {
    title: 'Get Your API Token',
    description: 'Generate an API token to authenticate SDK requests and start tracking.',
    icon: KeyRound,
  },
  {
    title: 'Complete SDK Quickstart',
    description: 'Follow the SDK Quickstart to install, configure, and instrument your code.',
    icon: Code,
  },
  {
    title: 'Verify Integration',
    description: 'Confirm your setup is working and start monitoring your LLM usage.',
    icon: BarChart3,
  },
]

const envContent = `ADEN_API_KEY=your-api-token
ADEN_API_URL=https://kube.acho.io`

export function HelpDialog({ open, onOpenChange }: HelpDialogProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [copied, setCopied] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

  const isFirstStep = currentStep === 0
  const isLastStep = currentStep === steps.length - 1
  const CurrentIcon = steps[currentStep].icon

  const goBack = () => {
    if (!isFirstStep) {
      setCurrentStep((prev) => prev - 1)
    }
  }

  const goNext = () => {
    if (!isLastStep) {
      setCurrentStep((prev) => prev + 1)
    }
  }

  const finish = () => {
    onOpenChange(false)
    setCurrentStep(0)
    navigate(`${location.pathname}#settings/developers`)
  }

  const copyEnvToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(envContent)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      console.error('Failed to copy')
    }
  }

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setCurrentStep(0)
    }
    onOpenChange(open)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-[520px] p-0 gap-0 overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-3 p-6 pb-2">
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
            <CurrentIcon className="h-5 w-5 text-primary" />
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-xs text-muted-foreground">
              Step {currentStep + 1} of {steps.length}
            </span>
            <DialogTitle className="text-lg font-semibold">
              {steps[currentStep].title}
            </DialogTitle>
          </div>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto px-6 h-[420px]">
          <DialogDescription className="sr-only">
            SDK onboarding walkthrough
          </DialogDescription>
          <p className="text-sm text-muted-foreground mb-4">
            {steps[currentStep].description}
          </p>

          {/* Step 1: Get Your API Token */}
          {currentStep === 0 && (
            <div className="flex flex-col gap-4">
              {/* Warning box */}
              <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
                <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <span>
                  Keep your API token secure. Never commit it to version control or expose it in client-side code.
                </span>
              </div>

              {/* Numbered steps */}
              <div className="flex flex-col gap-3">
                <NumberedStep
                  number={1}
                  title="Navigate to Settings → Developers"
                  subtitle="Find the API Keys section in your dashboard"
                />
                <NumberedStep
                  number={2}
                  title="Generate a new API token"
                  subtitle='Click "Generate New" and give it a descriptive name'
                />
                <NumberedStep
                  number={3}
                  title="Copy and store securely"
                  subtitle="The token is only shown once—save it immediately"
                />
              </div>

              {/* Code block */}
              <div className="bg-slate-50 border border-border rounded-lg p-4">
                <p className="text-sm font-medium mb-2">Add to your .env file:</p>
                <div className="relative bg-white border border-border rounded-md p-3">
                  <pre className="text-xs font-mono whitespace-pre-wrap break-all pr-8">
                    {envContent}
                  </pre>
                  <button
                    onClick={copyEnvToClipboard}
                    className="absolute top-2 right-2 w-7 h-7 border border-border rounded flex items-center justify-center bg-white hover:border-primary hover:text-primary transition-colors"
                  >
                    {copied ? (
                      <Check className="h-3.5 w-3.5" />
                    ) : (
                      <Copy className="h-3.5 w-3.5" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Complete SDK Quickstart */}
          {currentStep === 1 && (
            <div className="flex flex-col gap-4">
              {/* Info box */}
              <div className="flex items-center gap-3 p-4 bg-primary/5 border border-primary/20 rounded-lg">
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <BookOpen className="h-4 w-4 text-primary" />
                </div>
                <div className="flex flex-col gap-1">
                  <p className="text-sm font-medium">SDK Quickstart Guide</p>
                  <p className="text-xs text-muted-foreground">
                    Navigate to <strong className="text-foreground">Settings → Developers → SDK Quickstart</strong> for complete setup instructions.
                  </p>
                </div>
              </div>

              {/* Checklist */}
              <div className="flex flex-col gap-3">
                <p className="text-sm font-medium">The quickstart covers:</p>
                <ul className="flex flex-col gap-2">
                  <ChecklistItem text="Package installation & initialization" />
                  <ChecklistItem text="Instrumenting LLM calls" />
                  <ChecklistItem text="Tagging for cost allocation" />
                  <ChecklistItem text="Streaming support" />
                </ul>
              </div>

              {/* Tip box */}
              <div className="text-xs text-blue-600 bg-blue-50 border border-blue-200 rounded-lg p-3">
                <strong>Tip:</strong> The SDK Quickstart includes copy-paste code snippets tailored to your account.
              </div>
            </div>
          )}

          {/* Step 3: Verify Integration */}
          {currentStep === 2 && (
            <div className="flex flex-col gap-4">
              {/* Numbered steps */}
              <div className="flex flex-col gap-3">
                <NumberedStep
                  number={1}
                  title="Make a test request"
                  subtitle="Run the test code from the SDK Quickstart to send your first tracked request."
                />
                <div className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 text-xs font-semibold text-primary">
                    2
                  </div>
                  <div className="flex flex-col gap-1">
                    <p className="text-sm font-medium">Check your dashboard</p>
                    <p className="text-xs text-muted-foreground">
                      Within 30 seconds, you should see data appear in:
                    </p>
                    <ul className="flex flex-col gap-2 mt-2">
                      <li className="flex items-start gap-2 text-sm">
                        <Check className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
                        <span><strong>Analytics tab</strong> — Request counts and cost trends</span>
                      </li>
                      <li className="flex items-start gap-2 text-sm">
                        <Check className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
                        <span><strong>Data tab</strong> — Detailed request logs</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Warning/troubleshooting box */}
              <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
                <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <div className="flex flex-col gap-1">
                  <p className="font-semibold">Not seeing data?</p>
                  <ul className="text-xs space-y-0.5">
                    <li>Verify your API key is correct in .env</li>
                    <li>Ensure the SDK is initialized before LLM calls</li>
                    <li>Check for network/firewall issues</li>
                    <li>Review the troubleshooting section in Documentation</li>
                  </ul>
                </div>
              </div>

              {/* Help text */}
              <p className="text-xs text-muted-foreground pt-3 border-t">
                Need more help? Return to <strong className="text-foreground">Settings → Developers → Documentation</strong> for detailed troubleshooting.
              </p>
            </div>
          )}
        </div>

        {/* Progress Dots */}
        <div className="flex items-center justify-center gap-2 py-4">
          {steps.map((_, index) => (
            <button
              key={index}
              onClick={() => setCurrentStep(index)}
              className={cn(
                'w-2 h-2 rounded-full transition-colors',
                index === currentStep
                  ? 'bg-primary'
                  : 'bg-muted-foreground/30 hover:bg-muted-foreground/50'
              )}
            />
          ))}
        </div>

        {/* Footer */}
        <div className="flex justify-between p-6 pt-0">
          {!isFirstStep ? (
            <Button variant="outline" onClick={goBack}>
              <ChevronLeft className="h-4 w-4 mr-1" />
              Back
            </Button>
          ) : (
            <div />
          )}
          {!isLastStep ? (
            <Button onClick={goNext}>
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          ) : (
            <Button onClick={finish}>Get Started</Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

function NumberedStep({
  number,
  title,
  subtitle,
}: {
  number: number
  title: string
  subtitle: string
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 text-xs font-semibold text-primary">
        {number}
      </div>
      <div className="flex flex-col gap-0.5">
        <p className="text-sm font-medium">{title}</p>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </div>
    </div>
  )
}

function ChecklistItem({ text }: { text: string }) {
  return (
    <li className="flex items-start gap-2 text-sm">
      <Check className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
      <span>{text}</span>
    </li>
  )
}
