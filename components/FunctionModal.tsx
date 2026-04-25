'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';
import { X, Plus, Trash2, Play, Loader2 } from 'lucide-react';
import { useToast } from './ToastProvider';

const API_URL = '/api/';

interface FunctionModalProps {
  isOpen: boolean;
  onClose: () => void;
  agentId: number;
  functionData?: FunctionData | null;
  onSuccess?: () => void;
}

interface FunctionData {
  id?: number;
  name: string;
  description: string | null;
  method: string;
  url: string;
  timeout_ms: number;
  headers: Record<string, string>;
  query_params: Record<string, string>;
  parameters_schema: Record<string, any>;
  variables: Record<string, any>;
  speak_during_execution: boolean;
  speak_after_execution: boolean;
}

interface KeyValuePair {
  key: string;
  value: string;
}

interface ParameterField {
  name: string;
  description: string;
  type: 'string' | 'number' | 'boolean' | 'array' | 'object';
  required: boolean;
}

const HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'];
const PARAMETER_TYPES = ['string', 'number', 'boolean', 'array', 'object'];

const DEFAULT_FUNCTION: FunctionData = {
  name: '',
  description: '',
  method: 'POST',
  url: '',
  timeout_ms: 120000,
  headers: {},
  query_params: {},
  parameters_schema: {},
  variables: {},
  speak_during_execution: false,
  speak_after_execution: true,
};

const normalizeSpeechFlags = (value: Pick<FunctionData, 'speak_during_execution' | 'speak_after_execution'>) => {
  const during = Boolean(value.speak_during_execution);
  const after = Boolean(value.speak_after_execution);
  if ((during && !after) || (!during && after)) {
    return { speak_during_execution: during, speak_after_execution: after };
  }
  return { speak_during_execution: false, speak_after_execution: true };
};

export default function FunctionModal({ isOpen, onClose, agentId, functionData, onSuccess }: FunctionModalProps) {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [formData, setFormData] = useState<FunctionData>(DEFAULT_FUNCTION);
  const [headers, setHeaders] = useState<KeyValuePair[]>([{ key: '', value: '' }]);
  const [queryParams, setQueryParams] = useState<KeyValuePair[]>([{ key: '', value: '' }]);
  const [variables, setVariables] = useState<KeyValuePair[]>([{ key: '', value: '' }]);
  const [parametersJson, setParametersJson] = useState('');
  const [activeTab, setActiveTab] = useState<'json' | 'form'>('json');
  const [formParameters, setFormParameters] = useState<ParameterField[]>([]);

  // Convert JSON schema to form parameters
  const jsonToFormParams = (schema: Record<string, any>): ParameterField[] => {
    if (!schema || !schema.properties) return [];
    
    return Object.entries(schema.properties).map(([name, prop]: [string, any]) => ({
      name,
      description: prop.description || '',
      type: prop.type || 'string',
      required: (schema.required || []).includes(name),
    }));
  };

  // Convert form parameters to JSON schema
  const formParamsToJson = (params: ParameterField[]): Record<string, any> => {
    const properties: Record<string, any> = {};
    const required: string[] = [];

    params.forEach(param => {
      if (param.name) {
        properties[param.name] = {
          type: param.type,
          description: param.description,
        };
        if (param.required) {
          required.push(param.name);
        }
      }
    });

    return {
      type: 'object',
      properties,
      required,
    };
  };

  useEffect(() => {
    if (isOpen) {
      if (functionData) {
        setFormData({
          ...functionData,
          ...normalizeSpeechFlags(functionData),
        });
        setHeaders(Object.entries(functionData.headers || {}).map(([key, value]) => ({ key, value: String(value ?? '') })));
        setQueryParams(Object.entries(functionData.query_params || {}).map(([key, value]) => ({ key, value: String(value ?? '') })));
        setVariables(Object.entries(functionData.variables || {}).map(([key, value]) => ({ key, value: String(value ?? '') })));
        const schema = functionData.parameters_schema || {};
        setParametersJson(JSON.stringify(schema, null, 2));
        setFormParameters(jsonToFormParams(schema));
      } else {
        setFormData(DEFAULT_FUNCTION);
        setHeaders([{ key: '', value: '' }]);
        setQueryParams([{ key: '', value: '' }]);
        setVariables([{ key: '', value: '' }]);
        setParametersJson('');
        setFormParameters([]);
      }
    }
  }, [isOpen, functionData]);

  // Sync JSON to Form when switching tabs
  useEffect(() => {
    if (activeTab === 'form') {
      try {
        const schema = parametersJson ? JSON.parse(parametersJson) : {};
        setFormParameters(jsonToFormParams(schema));
      } catch (e) {
        // Invalid JSON, keep current form params
      }
    }
  }, [activeTab]);

  const addFormParameter = () => {
    setFormParameters([...formParameters, { name: '', description: '', type: 'string', required: false }]);
  };

  const updateFormParameter = (index: number, field: keyof ParameterField, value: any) => {
    const updated = [...formParameters];
    updated[index] = { ...updated[index], [field]: value };
    setFormParameters(updated);
    
    // Update JSON when form changes
    const schema = formParamsToJson(updated);
    setParametersJson(JSON.stringify(schema, null, 2));
  };

  const removeFormParameter = (index: number) => {
    const updated = formParameters.filter((_, i) => i !== index);
    setFormParameters(updated);
    
    // Update JSON when form changes
    const schema = formParamsToJson(updated);
    setParametersJson(JSON.stringify(schema, null, 2));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

      try {
        // Validate JSON before sending
        let parsedSchema = {};
        if (parametersJson) {
          try {
            parsedSchema = JSON.parse(parametersJson);
          } catch (jsonErr) {
            showToast('Invalid JSON in Parameters field. Please fix the JSON format.', 'error');
            return;
          }
        }

        const speechFlags = normalizeSpeechFlags(formData);
        const payload = {
          ...formData,
          ...speechFlags,
          headers: Object.fromEntries(headers.filter(h => h.key).map(h => [h.key, h.value])),
          query_params: Object.fromEntries(queryParams.filter(q => q.key).map(q => [q.key, q.value])),
          variables: Object.fromEntries(variables.filter(v => v.key).map(v => [v.key, v.value])),
          parameters_schema: parsedSchema,
        };

        console.log('Saving function:', payload);

        if (functionData?.id) {
          const res = await axios.patch(`${API_URL}agents/${agentId}/functions/${functionData.id}`, payload);
          console.log('Update response:', res.data);
          showToast('Function updated successfully', 'success');
        } else {
          const res = await axios.post(`${API_URL}agents/${agentId}/functions`, payload);
          console.log('Create response:', res.data);
          showToast('Function created successfully', 'success');
        }

        onSuccess?.();
        onClose();
      } catch (error: any) {
        console.error('Function save error:', error);
        const errorMsg = error?.response?.data?.detail || error?.message || 'Failed to save function';
        showToast(errorMsg, 'error');
      } finally {
        setLoading(false);
      }
  };

  const handleTest = async () => {
    setTesting(true);
    try {
      // Test the function endpoint
      const response = await axios.post(`${API_URL}agents/${agentId}/functions/test`, {
        url: formData.url,
        method: formData.method,
        headers: Object.fromEntries(headers.filter(h => h.key).map(h => [h.key, h.value])),
      });
      showToast('Function test successful', 'success');
    } catch (error) {
      showToast('Function test failed', 'error');
    } finally {
      setTesting(false);
    }
  };

  const addKeyValuePair = (setter: React.Dispatch<React.SetStateAction<KeyValuePair[]>>) => {
    setter(prev => [...prev, { key: '', value: '' }]);
  };

  const removeKeyValuePair = (setter: React.Dispatch<React.SetStateAction<KeyValuePair[]>>, index: number) => {
    setter(prev => prev.filter((_, i) => i !== index));
  };

  const updateKeyValuePair = (
    setter: React.Dispatch<React.SetStateAction<KeyValuePair[]>>,
    index: number,
    field: 'key' | 'value',
    value: string
  ) => {
    setter(prev => prev.map((item, i) => i === index ? { ...item, [field]: value } : item));
  };

  const formatJson = () => {
    try {
      const parsed = JSON.parse(parametersJson);
      setParametersJson(JSON.stringify(parsed, null, 2));
    } catch (e) {
      showToast('Invalid JSON', 'error');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-gray-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
            <h2 className="text-lg font-semibold text-gray-900">
              {functionData ? 'Edit Function' : 'Custom Function'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="overflow-y-auto max-h-[calc(90vh-140px)]">
          <div className="p-6 space-y-6">
            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Enter the name of the custom function"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                value={formData.description || ''}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Enter the description of the custom function"
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              />
            </div>

            {/* API Endpoint */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">API Endpoint</label>
              <p className="text-xs text-gray-500 mb-2">The API Endpoint is the address of the service you are connecting to</p>
              <div className="flex gap-2">
                <select
                  value={formData.method}
                  onChange={(e) => setFormData({ ...formData, method: e.target.value })}
                  className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                >
                  {HTTP_METHODS.map(method => (
                    <option key={method} value={method}>{method}</option>
                  ))}
                </select>
                <input
                  type="url"
                  value={formData.url}
                  onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                  placeholder="Enter the URL of the custom function"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  required
                />
              </div>
            </div>

            {/* Timeout */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Timeout (ms)</label>
              <div className="relative">
                <input
                  type="number"
                  value={formData.timeout_ms}
                  onChange={(e) => setFormData({ ...formData, timeout_ms: parseInt(e.target.value) || 120000 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  min="1000"
                  step="1000"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">milliseconds</span>
              </div>
            </div>

            {/* Headers */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Headers</label>
              <p className="text-xs text-gray-500 mb-2">Specify the HTTP headers required for your API request.</p>
              <div className="space-y-2">
                {headers.map((header, index) => (
                  <div key={index} className="flex gap-2">
                    <input
                      type="text"
                      value={header.key}
                      onChange={(e) => updateKeyValuePair(setHeaders, index, 'key', e.target.value)}
                      placeholder="Key"
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                    />
                    <input
                      type="text"
                      value={header.value}
                      onChange={(e) => updateKeyValuePair(setHeaders, index, 'value', e.target.value)}
                      placeholder="Value"
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                    />
                    <button
                      type="button"
                      onClick={() => removeKeyValuePair(setHeaders, index)}
                      className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => addKeyValuePair(setHeaders)}
                  className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 font-medium"
                >
                  <Plus className="w-4 h-4" />
                  New key value pair
                </button>
              </div>
            </div>

            {/* Query Parameters */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Query Parameters</label>
              <p className="text-xs text-gray-500 mb-2">Query string parameters to append to the URL.</p>
              <div className="space-y-2">
                {queryParams.map((param, index) => (
                  <div key={index} className="flex gap-2">
                    <input
                      type="text"
                      value={param.key}
                      onChange={(e) => updateKeyValuePair(setQueryParams, index, 'key', e.target.value)}
                      placeholder="Key"
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                    />
                    <input
                      type="text"
                      value={param.value}
                      onChange={(e) => updateKeyValuePair(setQueryParams, index, 'value', e.target.value)}
                      placeholder="Value"
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                    />
                    <button
                      type="button"
                      onClick={() => removeKeyValuePair(setQueryParams, index)}
                      className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => addKeyValuePair(setQueryParams)}
                  className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 font-medium"
                >
                  <Plus className="w-4 h-4" />
                  New key value pair
                </button>
              </div>
            </div>

            {/* Parameters (Optional) */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-700">Parameters (Optional)</label>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600">Payload: args only</span>
                  <div className="relative inline-block w-10 mr-2 align-middle select-none">
                    <input
                      type="checkbox"
                      className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 appearance-none cursor-pointer"
                    />
                  </div>
                </div>
              </div>
              <p className="text-xs text-gray-500 mb-2">JSON schema that defines the format in which the LLM will return. Please refer to the <a href="#" className="text-blue-600 hover:underline">docs</a>.</p>
              
              <div className="flex gap-2 mb-2">
                <button
                  type="button"
                  onClick={() => setActiveTab('json')}
                  className={`px-3 py-1 text-sm font-medium rounded ${activeTab === 'json' ? 'bg-gray-200 text-gray-900' : 'text-gray-600 hover:bg-gray-100'}`}
                >
                  JSON
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('form')}
                  className={`px-3 py-1 text-sm font-medium rounded ${activeTab === 'form' ? 'bg-gray-200 text-gray-900' : 'text-gray-600 hover:bg-gray-100'}`}
                >
                  Form
                </button>
              </div>

              {activeTab === 'json' ? (
                <>
                  <div className="relative">
                    <textarea
                      value={parametersJson}
                      onChange={(e) => setParametersJson(e.target.value)}
                      placeholder="Enter JSON Schema here..."
                      rows={8}
                      className="w-full px-3 py-2 bg-gray-900 text-gray-100 font-mono text-sm border border-gray-700 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                      spellCheck={false}
                    />
                  </div>

                  <div className="flex gap-2 mt-2">
                    <button type="button" className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded text-gray-700">example 1</button>
                    <button type="button" className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded text-gray-700">example 2</button>
                    <button type="button" className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded text-gray-700">example 3</button>
                  </div>

                  <button
                    type="button"
                    onClick={formatJson}
                    className="w-full mt-2 px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                  >
                    Format JSON
                  </button>
                </>
              ) : (
                <>
                  {/* Form View */}
                  <div className="border border-gray-200 rounded-lg overflow-hidden">
                    {/* Header */}
                    <div className="grid grid-cols-12 gap-2 px-3 py-2 bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-600">
                      <div className="col-span-3">Parameter Name</div>
                      <div className="col-span-5">Detail</div>
                      <div className="col-span-2">Type</div>
                      <div className="col-span-1">Required</div>
                      <div className="col-span-1"></div>
                    </div>
                    
                    {/* Parameter Rows */}
                    <div className="divide-y divide-gray-100">
                      {formParameters.map((param, index) => (
                        <div key={index} className="grid grid-cols-12 gap-2 px-3 py-2 items-center">
                          <div className="col-span-3">
                            <input
                              type="text"
                              value={param.name}
                              onChange={(e) => updateFormParameter(index, 'name', e.target.value)}
                              placeholder="postcode"
                              className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                            />
                          </div>
                          <div className="col-span-5">
                            <input
                              type="text"
                              value={param.description}
                              onChange={(e) => updateFormParameter(index, 'description', e.target.value)}
                              placeholder="Zone region in which the property is located"
                              className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                            />
                          </div>
                          <div className="col-span-2">
                            <select
                              value={param.type}
                              onChange={(e) => updateFormParameter(index, 'type', e.target.value)}
                              className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
                            >
                              {PARAMETER_TYPES.map(type => (
                                <option key={type} value={type}>{type}</option>
                              ))}
                            </select>
                          </div>
                          <div className="col-span-1 flex justify-center">
                            <input
                              type="checkbox"
                              checked={param.required}
                              onChange={(e) => updateFormParameter(index, 'required', e.target.checked)}
                              className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
                            />
                          </div>
                          <div className="col-span-1 flex justify-end">
                            <button
                              type="button"
                              onClick={() => removeFormParameter(index)}
                              className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  <button
                    type="button"
                    onClick={addFormParameter}
                    className="flex items-center gap-1 mt-3 text-sm text-blue-600 hover:text-blue-700 font-medium"
                  >
                    <Plus className="w-4 h-4" />
                    Add
                  </button>
                </>
              )}
            </div>

            {/* Store Fields as Variables */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Store Fields as Variables</label>
              <p className="text-xs text-gray-500 mb-2">Extract values from tool response and store as dynamic variables.</p>
              <div className="space-y-2">
                {variables.map((variable, index) => (
                  <div key={index} className="flex gap-2">
                    <input
                      type="text"
                      value={variable.key}
                      onChange={(e) => updateKeyValuePair(setVariables, index, 'key', e.target.value)}
                      placeholder="Key"
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                    />
                    <input
                      type="text"
                      value={variable.value}
                      onChange={(e) => updateKeyValuePair(setVariables, index, 'value', e.target.value)}
                      placeholder="Value"
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                    />
                    <button
                      type="button"
                      onClick={() => removeKeyValuePair(setVariables, index)}
                      className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => addKeyValuePair(setVariables)}
                  className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 font-medium"
                >
                  <Plus className="w-4 h-4" />
                  New key value pair
                </button>
              </div>
            </div>

            {/* Speak During Execution */}
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                id="speakDuring"
                checked={formData.speak_during_execution}
                onChange={(e) => {
                  if (!e.target.checked) return;
                  setFormData({
                    ...formData,
                    speak_during_execution: true,
                    speak_after_execution: false,
                  });
                }}
                className="mt-1 w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
              />
              <div>
                <label htmlFor="speakDuring" className="text-sm font-medium text-gray-700 cursor-pointer">Speak During Execution</label>
                <p className="text-xs text-gray-500">If the function takes over 2 seconds, the agent can say something like: "Let me check that for you."</p>
              </div>
            </div>

            {/* Speak After Execution */}
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                id="speakAfter"
                checked={formData.speak_after_execution}
                onChange={(e) => {
                  if (!e.target.checked) return;
                  setFormData({
                    ...formData,
                    speak_during_execution: false,
                    speak_after_execution: true,
                  });
                }}
                className="mt-1 w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
              />
              <div>
                <label htmlFor="speakAfter" className="text-sm font-medium text-gray-700 cursor-pointer">Speak After Execution</label>
                <p className="text-xs text-gray-500">Unselect if you want to run the function silently, such as uploading the call result to the server silently.</p>
              </div>
            </div>
            <p className="text-xs text-gray-500 -mt-1">
              Exactly one option is active at a time.
            </p>
          </div>
        </form>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            type="button"
            onClick={handleTest}
            disabled={testing || !formData.url}
            className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {testing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            Test
          </button>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              onClick={handleSubmit}
              disabled={loading || !formData.name || !formData.url}
              className="px-4 py-2 bg-gray-900 text-white rounded-md text-sm font-medium hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                'Save'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
