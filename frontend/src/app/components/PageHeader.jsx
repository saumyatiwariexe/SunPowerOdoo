import React from 'react'
import { Heading } from '../records'
export default function PageHeader({ title, action }) {
  return <Heading title={title}>{action}</Heading>
}
