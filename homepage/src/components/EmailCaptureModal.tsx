import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

interface EmailCaptureModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { email: string, company: string, volume: string }) => void;
}

const formSchema = z.object({
  email: z.string().email({ message: "Please enter a valid email address" }),
  company: z.string().min(1, { message: "Company name is required" }),
  volume: z.string().min(1, { message: "Order volume is required" })
});

const EmailCaptureModal: React.FC<EmailCaptureModalProps> = ({ isOpen, onClose, onSubmit }) => {
  const [volume, setVolume] = useState("0-500");
  
  const { register, handleSubmit, formState: { errors }, reset } = useForm({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: "",
      company: "",
      volume: "0-500"
    }
  });
  
  const handleFormSubmit = (data: any) => {
    onSubmit(data);
    reset();
    onClose();
  };
  
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold">Get your custom pricing quote</DialogTitle>
          <DialogDescription>
            We'll tailor a solution package for your business needs
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4 mt-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email address</Label>
            <Input 
              id="email" 
              type="email" 
              placeholder="you@company.com" 
              {...register("email")}
              className={errors.email ? "border-red-500" : ""}
            />
            {errors.email && (
              <p className="text-red-500 text-sm">{errors.email.message as string}</p>
            )}
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="company">Company name</Label>
            <Input 
              id="company" 
              placeholder="Your company" 
              {...register("company")}
              className={errors.company ? "border-red-500" : ""}
            />
            {errors.company && (
              <p className="text-red-500 text-sm">{errors.company.message as string}</p>
            )}
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="volume">Monthly order volume</Label>
            <Select 
              defaultValue="0-500"
              onValueChange={(value) => setVolume(value)}
            >
              <SelectTrigger id="volume">
                <SelectValue placeholder="Select volume" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="0-500">0-500 orders/month</SelectItem>
                <SelectItem value="501-2000">501-2,000 orders/month</SelectItem>
                <SelectItem value="2001-10000">2,001-10,000 orders/month</SelectItem>
                <SelectItem value="10001+">10,001+ orders/month</SelectItem>
              </SelectContent>
            </Select>
            <input type="hidden" {...register("volume")} value={volume} />
          </div>
          
          <Button 
            type="submit" 
            className="w-full bg-cratejoy-teal hover:bg-cratejoy-dark"
          >
            Get Custom Quote
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default EmailCaptureModal;
