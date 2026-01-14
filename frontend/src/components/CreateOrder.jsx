import React, { useState } from 'react';
import { Package, MapPin, Truck, CheckCircle, ArrowLeft, ArrowRight } from 'lucide-react';
import { ordersAPI } from '../services/api';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

const CreateOrder = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    // From Address
    shipFromName: '',
    shipFromAddressLine1: '',
    shipFromCity: '',
    shipFromState: '',
    shipFromPostalCode: '',
    shipFromPhone: '',
    
    // To Address
    shipToName: '',
    shipToAddressLine1: '',
    shipToCity: '',
    shipToState: '',
    shipToPostalCode: '',
    shipToPhone: '',
    
    // Package
    packageWeight: '',
    packageLength: '',
    packageWidth: '',
    packageHeight: '',
    
    // Carrier
    carrier: 'usps',
    serviceCode: 'usps_priority_mail',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await ordersAPI.createOrder({
        ...formData,
        packageWeight: parseFloat(formData.packageWeight),
        packageLength: parseFloat(formData.packageLength),
        packageWidth: parseFloat(formData.packageWidth),
        packageHeight: parseFloat(formData.packageHeight),
      });

      toast.success('Label created successfully!');
      navigate('/orders');
    } catch (error) {
      console.error('Error creating order:', error);
      toast.error(error.response?.data?.detail || 'Failed to create label');
    } finally {
      setLoading(false);
    }
  };

  const serviceOptions = {
    usps: [
      { label: 'Priority Mail', value: 'usps_priority_mail' },
      { label: 'First Class Mail', value: 'usps_first_class_mail' },
      { label: 'Ground Advantage', value: 'usps_ground_advantage' },
    ],
    fedex: [
      { label: 'FedEx Ground', value: 'fedex_ground' },
      { label: 'FedEx 2Day', value: 'fedex_2_day' },
      { label: 'FedEx Overnight', value: 'fedex_priority_overnight' },
    ],
    ups: [
      { label: 'UPS Ground', value: 'ups_ground' },
      { label: 'UPS 2nd Day Air', value: 'ups_2nd_day_air' },
      { label: 'UPS Next Day Air', value: 'ups_next_day_air' },
    ],
  };

  const steps = [
    { number: 1, title: 'From Address', icon: MapPin },
    { number: 2, title: 'To Address', icon: MapPin },
    { number: 3, title: 'Package Details', icon: Package },
    { number: 4, title: 'Carrier Selection', icon: Truck },
  ];

  const renderStepIndicator = () => (
    <div className="flex items-center justify-between mb-8">
      {steps.map((s, index) => {
        const Icon = s.icon;
        const isActive = step === s.number;
        const isCompleted = step > s.number;
        
        return (
          <React.Fragment key={s.number}>
            <div className="flex items-center gap-3">
              <div
                className="w-12 h-12 rounded-full flex items-center justify-center transition-all"
                style={{
                  backgroundColor: isActive || isCompleted ? '#F97316' : '#1E293B',
                  border: isActive ? '2px solid #F97316' : '2px solid #1E293B',
                }}
              >
                {isCompleted ? (
                  <CheckCircle size={24} color="white" />
                ) : (
                  <Icon size={24} color={isActive || isCompleted ? 'white' : '#94A3B8'} />
                )}
              </div>
              <div className="hidden md:block">
                <p className="font-medium">{s.title}</p>
                <p style={{ color: '#94A3B8', fontSize: '0.875rem' }}>Step {s.number}</p>
              </div>
            </div>
            {index < steps.length - 1 && (
              <div
                className="flex-1 h-1 mx-4"
                style={{
                  backgroundColor: step > s.number ? '#F97316' : '#1E293B',
                }}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );

  const renderStep1 = () => (
    <div className="space-y-4">
      <h3 className="text-xl font-semibold mb-4">Ship From Address</h3>
      
      <div>
        <label className="block mb-2 font-medium">Name *</label>
        <input
          data-testid="shipFromName"
          type="text"
          name="shipFromName"
          value={formData.shipFromName}
          onChange={handleChange}
          className="input"
          required
        />
      </div>

      <div>
        <label className="block mb-2 font-medium">Address *</label>
        <input
          data-testid="shipFromAddressLine1"
          type="text"
          name="shipFromAddressLine1"
          value={formData.shipFromAddressLine1}
          onChange={handleChange}
          className="input"
          required
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block mb-2 font-medium">City *</label>
          <input
            data-testid="shipFromCity"
            type="text"
            name="shipFromCity"
            value={formData.shipFromCity}
            onChange={handleChange}
            className="input"
            required
          />
        </div>
        <div>
          <label className="block mb-2 font-medium">State *</label>
          <input
            data-testid="shipFromState"
            type="text"
            name="shipFromState"
            value={formData.shipFromState}
            onChange={handleChange}
            className="input"
            maxLength="2"
            placeholder="CA"
            required
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block mb-2 font-medium">ZIP Code *</label>
          <input
            data-testid="shipFromPostalCode"
            type="text"
            name="shipFromPostalCode"
            value={formData.shipFromPostalCode}
            onChange={handleChange}
            className="input"
            placeholder="12345"
            required
          />
        </div>
        <div>
          <label className="block mb-2 font-medium">Phone</label>
          <input
            data-testid="shipFromPhone"
            type="tel"
            name="shipFromPhone"
            value={formData.shipFromPhone}
            onChange={handleChange}
            className="input"
          />
        </div>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="space-y-4">
      <h3 className="text-xl font-semibold mb-4">Ship To Address</h3>
      
      <div>
        <label className="block mb-2 font-medium">Name *</label>
        <input
          data-testid="shipToName"
          type="text"
          name="shipToName"
          value={formData.shipToName}
          onChange={handleChange}
          className="input"
          required
        />
      </div>

      <div>
        <label className="block mb-2 font-medium">Address *</label>
        <input
          data-testid="shipToAddressLine1"
          type="text"
          name="shipToAddressLine1"
          value={formData.shipToAddressLine1}
          onChange={handleChange}
          className="input"
          required
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block mb-2 font-medium">City *</label>
          <input
            data-testid="shipToCity"
            type="text"
            name="shipToCity"
            value={formData.shipToCity}
            onChange={handleChange}
            className="input"
            required
          />
        </div>
        <div>
          <label className="block mb-2 font-medium">State *</label>
          <input
            data-testid="shipToState"
            type="text"
            name="shipToState"
            value={formData.shipToState}
            onChange={handleChange}
            className="input"
            maxLength="2"
            placeholder="NY"
            required
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block mb-2 font-medium">ZIP Code *</label>
          <input
            data-testid="shipToPostalCode"
            type="text"
            name="shipToPostalCode"
            value={formData.shipToPostalCode}
            onChange={handleChange}
            className="input"
            placeholder="10001"
            required
          />
        </div>
        <div>
          <label className="block mb-2 font-medium">Phone</label>
          <input
            data-testid="shipToPhone"
            type="tel"
            name="shipToPhone"
            value={formData.shipToPhone}
            onChange={handleChange}
            className="input"
          />
        </div>
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="space-y-4">
      <h3 className="text-xl font-semibold mb-4">Package Details</h3>
      
      <div>
        <label className="block mb-2 font-medium">Weight (ounces) *</label>
        <input
          data-testid="packageWeight"
          type="number"
          step="0.1"
          name="packageWeight"
          value={formData.packageWeight}
          onChange={handleChange}
          className="input"
          required
        />
        <p style={{ color: '#94A3B8', fontSize: '0.875rem', marginTop: '0.5rem' }}>
          16 oz = 1 lb
        </p>
      </div>

      <div>
        <label className="block mb-2 font-medium">Dimensions (inches)</label>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <input
              data-testid="packageLength"
              type="number"
              step="0.1"
              name="packageLength"
              value={formData.packageLength}
              onChange={handleChange}
              className="input"
              placeholder="Length"
              required
            />
          </div>
          <div>
            <input
              data-testid="packageWidth"
              type="number"
              step="0.1"
              name="packageWidth"
              value={formData.packageWidth}
              onChange={handleChange}
              className="input"
              placeholder="Width"
              required
            />
          </div>
          <div>
            <input
              data-testid="packageHeight"
              type="number"
              step="0.1"
              name="packageHeight"
              value={formData.packageHeight}
              onChange={handleChange}
              className="input"
              placeholder="Height"
              required
            />
          </div>
        </div>
      </div>
    </div>
  );

  const renderStep4 = () => (
    <div className="space-y-4">
      <h3 className="text-xl font-semibold mb-4">Carrier Selection</h3>
      
      <div>
        <label className="block mb-2 font-medium">Carrier *</label>
        <div className="grid grid-cols-3 gap-4">
          {['usps', 'fedex', 'ups'].map((carrier) => (
            <button
              key={carrier}
              data-testid={`carrier-${carrier}`}
              type="button"
              className="p-4 rounded border-2 transition-all"
              style={{
                borderColor: formData.carrier === carrier ? '#F97316' : '#1E293B',
                backgroundColor: formData.carrier === carrier ? 'rgba(249, 115, 22, 0.1)' : 'transparent',
              }}
              onClick={() => {
                setFormData(prev => ({
                  ...prev,
                  carrier,
                  serviceCode: serviceOptions[carrier][0].value,
                }));
              }}
            >
              <Package size={32} color={formData.carrier === carrier ? '#F97316' : '#94A3B8'} className="mx-auto mb-2" />
              <p className="font-semibold uppercase">{carrier}</p>
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block mb-2 font-medium">Service *</label>
        <select
          data-testid="serviceCode"
          name="serviceCode"
          value={formData.serviceCode}
          onChange={handleChange}
          className="input"
          required
        >
          {serviceOptions[formData.carrier]?.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );

  return (
    <div className="p-8">
      <div className="flex items-center gap-4 mb-8">
        <button
          data-testid="back-btn"
          onClick={() => navigate('/orders')}
          className="btn-secondary"
        >
          <ArrowLeft size={20} />
        </button>
        <div>
          <h1 data-testid="create-order-title" className="text-4xl font-bold">Create Shipping Label</h1>
          <p className="text-muted" style={{ color: '#94A3B8' }}>Fill in the details to create a new label</p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto">
        <div className="card mb-6">
          {renderStepIndicator()}
        </div>

        <form onSubmit={handleSubmit}>
          <div className="card">
            {step === 1 && renderStep1()}
            {step === 2 && renderStep2()}
            {step === 3 && renderStep3()}
            {step === 4 && renderStep4()}

            <div className="flex justify-between mt-8 pt-6" style={{ borderTop: '1px solid #1E293B' }}>
              {step > 1 ? (
                <button
                  data-testid="prev-step-btn"
                  type="button"
                  className="btn-secondary flex items-center gap-2"
                  onClick={() => setStep(step - 1)}
                >
                  <ArrowLeft size={20} />
                  Previous
                </button>
              ) : (
                <div />
              )}

              {step < 4 ? (
                <button
                  data-testid="next-step-btn"
                  type="button"
                  className="btn-primary flex items-center gap-2"
                  onClick={() => setStep(step + 1)}
                >
                  Next
                  <ArrowRight size={20} />
                </button>
              ) : (
                <button
                  data-testid="submit-order-btn"
                  type="submit"
                  className="btn-primary"
                  disabled={loading}
                >
                  {loading ? 'Creating Label...' : 'Create Label'}
                </button>
              )}
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateOrder;
